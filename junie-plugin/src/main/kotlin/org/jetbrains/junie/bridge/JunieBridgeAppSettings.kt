package org.jetbrains.junie.bridge

import com.intellij.openapi.components.BaseState
import com.intellij.openapi.components.SimplePersistentStateComponent
import com.intellij.openapi.components.State
import com.intellij.openapi.components.Storage

@State(
  name = "JunieBridgeAppSettings",
  storages = [Storage("junie_bridge.xml")]
)
class JunieBridgeAppSettings : SimplePersistentStateComponent<JunieBridgeAppSettings.State>(State()) {
  class State : BaseState() {
    var baseUrl by string("https://localhost:8765")
    var token by string("iamthatiammerkaba1144")
    var pollMillis by property(2000)
  }

  companion object {
    fun getInstance(): JunieBridgeAppSettings = service()
  }
}
