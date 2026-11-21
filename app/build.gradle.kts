plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

val run = (System.getenv("GITHUB_RUN_NUMBER") ?: "1").toInt()

android {
    namespace = "com.trtv"
    compileSdk = 36
    defaultConfig {
        applicationId = "com.trtv"
        minSdk = 28
        targetSdk = 36
        versionCode = run
        versionName = "1.$run"
    }
    signingConfigs {
        getByName("debug") {
            storeFile = rootProject.file("debug.p12")
            storePassword = "android"
            keyAlias = "1"
            keyPassword = "android"
            storeType = "pkcs12"
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    packaging { resources.excludes += "META-INF/*" }
}

kotlin { jvmToolchain(17) }
