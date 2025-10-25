package org.jetbrains.junie.bridge

import okhttp3.OkHttpClient
import java.security.SecureRandom
import java.security.cert.X509Certificate
import javax.net.ssl.HostnameVerifier
import javax.net.ssl.SSLContext
import javax.net.ssl.TrustManager
import javax.net.ssl.X509TrustManager

object Http {
  /**
   * OkHttp client that accepts self-signed certs for localhost/127.0.0.1 only.
   * Do NOT use this for non-local endpoints.
   */
  fun clientForLocalhost(): OkHttpClient {
    val trustAll = object : X509TrustManager {
      override fun checkClientTrusted(chain: Array<out X509Certificate>?, authType: String?) {}
      override fun checkServerTrusted(chain: Array<out X509Certificate>?, authType: String?) {}
      override fun getAcceptedIssuers(): Array<X509Certificate> = emptyArray()
    }
    val ssl = SSLContext.getInstance("TLS")
    ssl.init(null, arrayOf<TrustManager>(trustAll), SecureRandom())
    val sslSocketFactory = ssl.socketFactory

    val hostnameVerifier = HostnameVerifier { hostname, _ ->
      hostname == "localhost" || hostname == "127.0.0.1"
    }

    return OkHttpClient.Builder()
      .sslSocketFactory(sslSocketFactory, trustAll)
      .hostnameVerifier(hostnameVerifier)
      .build()
  }
}
