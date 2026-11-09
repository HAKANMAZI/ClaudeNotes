plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "com.hasan.ekrantemizle"
    compileSdk = 34

    defaultConfig {
        applicationId = "com.hasan.ekrantemizle"
        minSdk = 30
        targetSdk = 34
        versionCode = 2
        versionName = "2.0"
    }

    // Sabit imza: güncellemeler eski sürümün üstüne kurulabilsin
    signingConfigs {
        getByName("debug") {
            storeFile = file("sabit.keystore")
            storePassword = "ekrantemizle"
            keyAlias = "ekran"
            keyPassword = "ekrantemizle"
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions { jvmTarget = "17" }
}

dependencies {
    implementation("androidx.work:work-runtime-ktx:2.9.1")
}
