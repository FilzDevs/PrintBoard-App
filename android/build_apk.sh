#!/usr/bin/env bash
set -euo pipefail

SDK="/opt/android-sdk-linux"
BUILD_TOOLS="$SDK/build-tools/34.0.0"
PLATFORM="$SDK/platforms/android-34/android.jar"

rm -rf build
mkdir -p build/gen build/obj build/dex build/res

echo "[1/6] Compiling resources with aapt2..."
"$BUILD_TOOLS/aapt2" compile --dir src/main/res -o build/res.zip

echo "[2/6] Linking resources & AndroidManifest.xml..."
"$BUILD_TOOLS/aapt2" link \
    -o build/unaligned.apk \
    -I "$PLATFORM" \
    --manifest src/main/AndroidManifest.xml \
    --java build/gen \
    --auto-add-overlay \
    build/res.zip

echo "[3/6] Compiling Java sources with javac..."
find src/main/java build/gen -name "*.java" > build/sources.txt
javac -source 1.8 -target 1.8 \
    -Xlint:-options \
    -encoding UTF-8 \
    -cp "$PLATFORM" \
    -d build/obj \
    @build/sources.txt

echo "[4/6] Converting bytecode to DEX with d8..."
find build/obj -name "*.class" > build/classes.txt
"$BUILD_TOOLS/d8" \
    --min-api 24 \
    --lib "$PLATFORM" \
    --output build/dex \
    @build/classes.txt

echo "[5/6] Packaging classes.dex & zipaligning..."
cp build/dex/classes.dex .
zip -q -j build/unaligned.apk classes.dex
rm -f classes.dex

"$BUILD_TOOLS/zipalign" -f -p 4 build/unaligned.apk build/aligned.apk

echo "[6/6] Signing APK with apksigner..."
if [ ! -f build/keystore.jks ]; then
    keytool -genkeypair \
        -keystore build/keystore.jks \
        -alias printboard \
        -keyalg RSA \
        -keysize 2048 \
        -validity 10000 \
        -storepass printboard123 \
        -keypass printboard123 \
        -dname "CN=PrintBoard, OU=Mobile, O=PrintBoard, L=DE, S=DE, C=DE"
fi

"$BUILD_TOOLS/apksigner" sign \
    --ks build/keystore.jks \
    --ks-key-alias printboard \
    --ks-pass pass:printboard123 \
    --key-pass pass:printboard123 \
    --out /work/PrintBoard.apk \
    build/aligned.apk

"$BUILD_TOOLS/apksigner" verify --verbose /work/PrintBoard.apk
echo "Build successful: /work/PrintBoard.apk"
