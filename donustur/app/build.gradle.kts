plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "com.hasan.donustur"
    compileSdk = 34

    defaultConfig {
        applicationId = "com.hasan.donustur"
        minSdk = 29
        targetSdk = 34
        versionCode = 1
        versionName = "1.0"
    }

    // Sabit imza: güncellemeler eski sürümün üstüne kurulabilsin
    signingConfigs {
        getByName("debug") {
            storeFile = file("sabit.keystore")
            storePassword = "donustur"
            keyAlias = "donustur"
            keyPassword = "donustur"
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions { jvmTarget = "17" }
    packaging { resources.excludes += setOf("META-INF/*") }
}

dependencies {
    // PDF düzenleme (birleştir, böl, yazı, filigran, imza, şifre)
    implementation("com.tom-roush:pdfbox-android:2.0.27.0")
}
