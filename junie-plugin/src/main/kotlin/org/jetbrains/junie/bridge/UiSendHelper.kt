package org.jetbrains.junie.bridge

import com.intellij.openapi.project.Project
import com.intellij.openapi.wm.ToolWindowManager
import com.intellij.ui.EditorTextField
import javax.swing.JButton
import javax.swing.JComponent
import javax.swing.text.JTextComponent
import java.awt.Component

/**
 * Best-effort UI automation to send text into the Junie tool window.
 * Replace with a stable internal API when available.
 */
object UiSendHelper {
  fun sendIntoJunie(project: Project, text: String) {
    val twm = ToolWindowManager.getInstance(project)
    val id = twm.toolWindowIds.firstOrNull { id ->
      val tw = twm.getToolWindow(id)
      id.equals("Junie", true) || (tw?.stripeTitle?.contains("Junie", true) == true)
    } ?: return
    val tw = twm.getToolWindow(id) ?: return
    val content = tw.contentManager.selectedContent?.component ?: return

    // Prefer EditorTextField if present, otherwise fall back to JTextComponent
    val editorField = findEditorTextField(content)
    if (editorField != null) {
      editorField.text = text
    } else {
      val input = findTextComponent(content) ?: return
      input.text = text
    }

    val sendBtn = findButton(content, "Send")
    sendBtn?.doClick()
  }

  private fun findEditorTextField(root: Component): EditorTextField? {
    if (root is EditorTextField) return root
    if (root is JComponent) {
      for (child in root.components) {
        val found = findEditorTextField(child)
        if (found != null) return found
      }
    }
    return null
  }

  private fun findTextComponent(root: Component): JTextComponent? {
    if (root is JTextComponent) return root
    if (root is JComponent) {
      for (child in root.components) {
        val found = findTextComponent(child)
        if (found != null) return found
      }
    }
    return null
  }

  private fun findButton(root: Component, labelContains: String): JButton? {
    if (root is JButton && root.text?.contains(labelContains, ignoreCase = true) == true) return root
    if (root is JComponent) {
      for (child in root.components) {
        val found = findButton(child, labelContains)
        if (found != null) return found
      }
    }
    return null
  }
}
