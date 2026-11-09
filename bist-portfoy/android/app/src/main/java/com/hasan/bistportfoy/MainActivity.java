package com.hasan.bistportfoy;

import android.app.Activity;
import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import android.webkit.JavascriptInterface;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import org.json.JSONObject;
import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.URL;

public class MainActivity extends Activity {
  private WebView web;

  @Override protected void onCreate(Bundle b) {
    super.onCreate(b);
    web = new WebView(this);
    WebSettings s = web.getSettings();
    s.setJavaScriptEnabled(true);
    s.setDomStorageEnabled(true);
    web.addJavascriptInterface(new Bridge(), "Native");
    web.setWebViewClient(new WebViewClient() {
      // Dış linkler (Sheet, KAP) tarayıcıda açılsın
      @Override public boolean shouldOverrideUrlLoading(WebView v, WebResourceRequest r) {
        Uri u = r.getUrl();
        if ("file".equals(u.getScheme())) return false;
        try { startActivity(new Intent(Intent.ACTION_VIEW, u)); } catch (Exception e) { }
        return true;
      }
    });
    setContentView(web);
    if (b == null) web.loadUrl("file:///android_asset/index.html"); else web.restoreState(b);
  }

  // Tarayıcıdaki CORS sınırına takılmadan Yahoo Finance ve Apps Script'e HTTP GET
  private class Bridge {
    @JavascriptInterface public void get(final String id, final String url) {
      new Thread(new Runnable() { public void run() {
        boolean ok = false; String body;
        try {
          HttpURLConnection c = (HttpURLConnection) new URL(url).openConnection();
          c.setInstanceFollowRedirects(true);
          c.setConnectTimeout(15000);
          c.setReadTimeout(45000);
          c.setRequestProperty("User-Agent", "Mozilla/5.0 (Android) BistPortfoy/1.0");
          int code = c.getResponseCode();
          InputStream in = code < 400 ? c.getInputStream() : c.getErrorStream();
          body = in == null ? "" : read(in);
          ok = code < 400;
          if (!ok) body = "HTTP " + code;
        } catch (Exception e) { body = String.valueOf(e.getMessage()); }
        final String js = "window.__nativeCb(" + JSONObject.quote(id) + "," + ok + "," + JSONObject.quote(body) + ")";
        web.post(new Runnable() { public void run() { web.evaluateJavascript(js, null); } });
      }}).start();
    }
  }

  private static String read(InputStream in) throws Exception {
    ByteArrayOutputStream out = new ByteArrayOutputStream();
    byte[] buf = new byte[16384]; int n;
    while ((n = in.read(buf)) > 0) out.write(buf, 0, n);
    in.close();
    return out.toString("UTF-8");
  }

  @Override public void onBackPressed() {
    web.evaluateJavascript("window.onAndroidBack ? window.onAndroidBack() : false", new android.webkit.ValueCallback<String>() {
      public void onReceiveValue(String handled) { if (!"true".equals(handled)) MainActivity.super.onBackPressed(); }
    });
  }
  @Override protected void onSaveInstanceState(Bundle o) { super.onSaveInstanceState(o); web.saveState(o); }
  @Override protected void onPause() { super.onPause(); web.onPause(); }
  @Override protected void onResume() { super.onResume(); web.onResume(); }
}
