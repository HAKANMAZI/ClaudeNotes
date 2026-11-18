plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "com.hasan.videoindirici"
    compileSdk = 36

    defaultConfig {
        applicationId = "com.hasan.videoindirici"
        minSdk = 29             // Android 10 ve üstü (İndirilenler klasörüne izin istemeden kaydeder)
        targetSdk = 36
        versionCode = 3
        versionName = "2.1"
    }

    // Her işlemci türüne ayrı APK: boyut yarıya iner
    splits {
        abi {
            isEnable = true
            reset()
            include("arm64-v8a", "armeabi-v7a")
            isUniversalApk = false
        }
    }

    signingConfigs {
        // Sabit imza: yeni sürümler eskisinin üstüne kurulabilsin
        create("sabit") {
            storeFile = file("sabit.keystore")
            storePassword = "videoindir"
            keyAlias = "video"
            keyPassword = "videoindir"
        }
    }

    buildTypes {
        // Yayın sürümü: hata ayıklama kapalı (daha güvenli)
        release {
            isMinifyEnabled = false
            signingConfig = signingConfigs.getByName("sabit")
        }
    }

    // yt-dlp ve ffmpeg dosyaları telefona açılarak kurulmalı
    packaging { jniLibs.useLegacyPackaging = true }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}

dependencies {
    implementation("androidx.core:core-ktx:1.16.0")
    implementation("androidx.activity:activity-ktx:1.10.1")
    implementation("androidx.appcompat:appcompat:1.7.0")
    implementation("com.google.android.material:material:1.12.0")
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.9.1")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.10.2")
    // yt-dlp (YouTube ve bin sekiz yüzü aşkın site) + ffmpeg (MP3 dönüştürme, MP4 birleştirme)
    implementation("io.github.junkfood02.youtubedl-android:library:0.17.4")
    implementation("io.github.junkfood02.youtubedl-android:ffmpeg:0.17.4")
}

kotlin {
    compilerOptions { jvmTarget.set(org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_17) }
}
