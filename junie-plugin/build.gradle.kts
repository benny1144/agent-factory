plugins {
    id("org.jetbrains.intellij") version "1.17.3"
    kotlin("jvm") version "1.9.24"
}

repositories {
    mavenCentral()
}

kotlin {
    jvmToolchain(21)
}

intellij {
    type.set("IU") // or "IC" if Community
    version.set("2025.2")
    plugins.set(listOf())
}

tasks {
    patchPluginXml {
        sinceBuild.set("252")
        untilBuild.set("252.*")
    }
    buildSearchableOptions {
        enabled = false
    }
}

dependencies {
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    implementation("com.squareup.okio:okio:3.9.0")
}
