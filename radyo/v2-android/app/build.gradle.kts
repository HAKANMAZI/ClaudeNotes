plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "com.hasan.radyo"
    compileSdk = 36

    defaultConfig {
        applicationId = "com.hasan.radyo"
        minSdk = 26
        targetSdk = 36          // Google Play'in güncel hedef sürüm şartı
        versionCode = 12         // Play'e her yeni yüklemede bir artırın
        versionName = "2.8"
    }

    signingConfigs {
        // Telefona doğrudan kurmak için sabit imza (güncellemeler üstüne kurulur)
        getByName("debug") {
            storeFile = file("sabit.keystore")
            storePassword = "radyo123"
            keyAlias = "radyo"
            keyPassword = "radyo123"
        }
        // Google Play'e yükleme imzası: anahtar GitHub "Secrets" bölümünden gelir, depoda durmaz
        create("yukleme") {
            System.getenv("UPLOAD_KEYSTORE")?.let {
                storeFile = file(it)
                storePassword = System.getenv("UPLOAD_STORE_PASSWORD")
                keyAlias = System.getenv("UPLOAD_KEY_ALIAS")
                keyPassword = System.getenv("UPLOAD_KEY_PASSWORD")
            }
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            if (System.getenv("UPLOAD_KEYSTORE") != null) signingConfig = signingConfigs.getByName("yukleme")
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions { jvmTarget = "17" }
}

dependencies {
    implementation("androidx.core:core-ktx:1.16.0")
    implementation("androidx.activity:activity-ktx:1.10.1")
    implementation("androidx.webkit:webkit:1.13.0")
    // Google Play ödeme sistemi: sadece gönüllü destek (bağış) için
    implementation("com.android.billingclient:billing-ktx:7.1.1")
}
