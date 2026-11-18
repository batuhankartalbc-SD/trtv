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
        versionName = "0.$run"
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

dependencies {
    implementation("dev.mobile:dadb:2.0.0")
    implementation("dev.rikka.shizuku:api:13.1.5")
    implementation("dev.rikka.shizuku:provider:13.1.5")
}
