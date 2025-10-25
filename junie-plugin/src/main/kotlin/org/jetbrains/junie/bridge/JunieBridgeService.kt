package org.jetbrains.junie.bridge

import com.intellij.openapi.Disposable
import com.intellij.openapi.application.ApplicationManager
import com.intellij.openapi.components.Service
import com.intellij.openapi.diagnostic.Logger
import com.intellij.openapi.project.Project
import com.intellij.openapi.wm.ToolWindowManager
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import java.net.URLEncoder
import java.nio.charset.StandardCharsets
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit

@Service(Service.Level.PROJECT)
class JunieBridgeService(private val project: Project) : Disposable {
  private val log = Logger.getInstance(JunieBridgeService::class.java)
  private val client = Http.clientForLocalhost()
  private val exec = Executors.newSingleThreadScheduledExecutor { r ->
    Thread(r, "JunieBridgePoller-${project.name}").apply { isDaemon = true }
  }

  @Volatile private var lastSeenId: String? = null

  init {
    val settings = JunieBridgeAppSettings.getInstance().state
    log.info("Starting JunieBridgeService poller every ${settings.pollMillis} ms against ${settings.baseUrl}")
    exec.scheduleWithFixedDelay({ safePoll(settings) }, 0, settings.pollMillis.toLong(), TimeUnit.MILLISECONDS)
  }

  private fun safePoll(settings: JunieBridgeAppSettings.State) {
    try {
      pollOnce(settings)
    } catch (t: Throwable) {
      log.warn("Polling error", t)
    }
  }

  private fun pollOnce(settings: JunieBridgeAppSettings.State) {
    val base = settings.baseUrl.trimEnd('/')
    val roles = "gpt"
    val max = 5
    val qs = buildString {
      append("?roles=").append(URLEncoder.encode(roles, StandardCharsets.UTF_8))
      append("&max=").append(max)
      lastSeenId?.let { append("&sinceId=").append(URLEncoder.encode(it, StandardCharsets.UTF_8)) }
    }
    log.info("Polling bridge $base/messages/pull for roles=$roles sinceId=${lastSeenId}")

    val req = Request.Builder()
      .url("$base/messages/pull$qs")
      .addHeader("X-Junie-Token", settings.token)
      .get()
      .build()

    client.newCall(req).execute().use { resp ->
      if (!resp.isSuccessful) return
      val body = resp.body?.string().orEmpty()
      val msgs = Json.simpleExtractMessages(body)
      if (msgs.isEmpty()) return
      log.info("Received ${msgs.size} message(s) from bridge")

      for (m in msgs) {
        lastSeenId = m.id
        if (m.role == "gpt") {
          log.info("Received GPT message id=${m.id} len=${m.text.length}")
          bringJunieToFront()
          sendToJunieUi(m.text)
          ack(listOf(m.id), settings)
        }
      }
    }
  }

  private fun ack(ids: List<String>, settings: JunieBridgeAppSettings.State) {
    val base = settings.baseUrl.trimEnd('/')
    val json = """{"ids":[${ids.joinToString(",") { "\"$it\"" }}]}"""
    val req = Request.Builder()
      .url("$base/messages/ack")
      .addHeader("X-Junie-Token", settings.token)
      .post(json.toRequestBody("application/json".toMediaType()))
      .build()
    client.newCall(req).execute().use { }
    log.info("Acknowledge ids=$ids")
  }

  fun ingestReply(text: String, settings: JunieBridgeAppSettings.State = JunieBridgeAppSettings.getInstance().state) {
    val base = settings.baseUrl.trimEnd('/')
    val json = """{"text":${Json.q(text)}}"""
    val req = Request.Builder()
      .url("$base/messages/hitl/ingest")
      .addHeader("X-Junie-Token", settings.token)
      .post(json.toRequestBody("application/json".toMediaType()))
      .build()
    client.newCall(req).execute().use { }
    log.info("Ingested reply len=${text.length}")
  }

  private fun bringJunieToFront() {
    ApplicationManager.getApplication().invokeLater {
      val twm = ToolWindowManager.getInstance(project)
      val id = twm.toolWindowIds.firstOrNull { id ->
        val tw = twm.getToolWindow(id)
        id.equals("Junie", true) || (tw?.stripeTitle?.contains("Junie", true) == true)
      } ?: return@invokeLater
      val tw = twm.getToolWindow(id) ?: return@invokeLater
      tw.show()
    }
  }

  private fun sendToJunieUi(text: String) {
    ApplicationManager.getApplication().invokeLater {
      try {
        UiSendHelper.sendIntoJunie(project, text)
      } catch (t: Throwable) {
        log.warn("Failed to send text into Junie UI", t)
      }
    }
  }

  override fun dispose() {
    exec.shutdownNow()
  }
}

// ---------- Minimal JSON helpers (avoid heavy deps) ----------
object Json {
  data class Msg(val id: String, val role: String, val text: String)
  fun simpleExtractMessages(json: String): List<Msg> {
    val result = mutableListOf<Msg>()
    val arrStart = json.indexOf("\"messages\"")
    if (arrStart < 0) return result
    var i = json.indexOf('[', arrStart)
    if (i < 0) return result
    var depth = 0
    val items = StringBuilder()
    while (++i < json.length) {
      val c = json[i]
      if (c == '[') depth++
      if (c == ']') { if (depth == 0) break else depth-- }
      items.append(c)
    }
    val s = items.toString()
    val chunks = s.split(Regex("},\\s*\\{")).map {
      var t = it
      if (!t.startsWith("{")) t = "{$t"
      if (!t.endsWith("}")) t = "$t}"
      t
    }
    for (ch in chunks) {
      val id = findJsonString(ch, "id") ?: continue
      val role = findJsonString(ch, "role") ?: continue
      val text = findJsonString(ch, "text") ?: ""
      result.add(Msg(id, role, unescape(text)))
    }
    return result
  }
  private fun findJsonString(s: String, key: String): String? {
    val r = Regex("\"$key\"\\s*:\\s*\"((?:\\\\.|[^\"\\\\])*)\"")
    val m = r.find(s) ?: return null
    return m.groupValues[1]
  }
  fun q(s: String): String = "\"" + s.replace("\\", "\\\\").replace("\"", "\\\"").replace("\n", "\\n").replace("\r", "\\r") + "\""
  private fun unescape(s: String): String =
    s.replace("\\n", "\n").replace("\\r", "\r").replace("\\\"", "\"").replace("\\\\", "\\")
}
