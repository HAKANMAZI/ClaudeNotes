package com.hasan.radyo

import android.app.Activity
import com.android.billingclient.api.AcknowledgePurchaseParams
import com.android.billingclient.api.BillingClient
import com.android.billingclient.api.BillingClientStateListener
import com.android.billingclient.api.BillingFlowParams
import com.android.billingclient.api.BillingResult
import com.android.billingclient.api.ConsumeParams
import com.android.billingclient.api.PendingPurchasesParams
import com.android.billingclient.api.ProductDetails
import com.android.billingclient.api.Purchase
import com.android.billingclient.api.PurchasesUpdatedListener
import com.android.billingclient.api.QueryProductDetailsParams
import com.android.billingclient.api.QueryPurchasesParams
import org.json.JSONArray
import org.json.JSONObject

/**
 * GÖNÜLLÜ DESTEK (bağış)
 *
 * Uygulamada reklam ve abonelik yok. Kullanıcı isterse gönüllü olarak
 * destek olabilir; destek hiçbir özelliği açmaz.
 *
 * Google Play kuralı gereği geliştiriciye yapılan bağışlar Google Play'in
 * ödeme sistemiyle alınır. Bu yüzden Play Console'da üç "tek seferlik ürün"
 * oluşturulmalı (kimlikleri aşağıda). Ürünler satın alınınca hemen
 * "tüketilir"; böylece kullanıcı istediği kadar tekrar destek olabilir.
 *
 * Uygulama Google Play'den indirilmediyse (APK ile kurulduysa) bu bölüm
 * çalışmaz; uygulamanın geri kalanı normal çalışır.
 */
class Destek(
    private val etkinlik: Activity,
    private val js: (String) -> Unit   // Sonucu web sayfasına bildirmek için
) : PurchasesUpdatedListener {

    /** Play Console > Para kazanma > Uygulama içi ürünler'de bu kimliklerle oluşturun */
    private val urunKimlikleri = listOf("destek_kucuk", "destek_orta", "destek_buyuk")

    private val istemci: BillingClient = BillingClient.newBuilder(etkinlik)
        .setListener(this)
        .enablePendingPurchases(PendingPurchasesParams.newBuilder().enableOneTimeProducts().build())
        .enableAutoServiceReconnection() // Bağlantı koparsa kendiliğinden yeniden bağlan
        .build()

    @Volatile private var urunler: List<ProductDetails> = emptyList()

    fun baglan() {
        if (istemci.isReady) { urunleriGetir(); return }
        istemci.startConnection(object : BillingClientStateListener {
            override fun onBillingSetupFinished(sonuc: BillingResult) {
                if (sonuc.responseCode == BillingClient.BillingResponseCode.OK) {
                    urunleriGetir()
                    eskileriTamamla()
                }
            }
            override fun onBillingServiceDisconnected() { }
        })
    }

    fun kapat() { if (istemci.isReady) istemci.endConnection() }

    private fun urunleriGetir() {
        val params = QueryProductDetailsParams.newBuilder()
            .setProductList(urunKimlikleri.map {
                QueryProductDetailsParams.Product.newBuilder()
                    .setProductId(it)
                    .setProductType(BillingClient.ProductType.INAPP)
                    .build()
            })
            .build()
        istemci.queryProductDetailsAsync(params) { _, sonuc ->
            // Ucuzdan pahalıya sırala
            urunler = sonuc.productDetailsList.sortedBy { it.oneTimePurchaseOfferDetails?.priceAmountMicros ?: 0L }
        }
    }

    /** Web sayfasına ürün listesi: [{id, name, price}] */
    fun urunlerJson(): String {
        val dizi = JSONArray()
        urunler.forEach {
            dizi.put(JSONObject()
                .put("id", it.productId)
                .put("name", it.name)
                .put("price", it.oneTimePurchaseOfferDetails?.formattedPrice ?: ""))
        }
        return dizi.toString()
    }

    fun satinAl(id: String) {
        val urun = urunler.firstOrNull { it.productId == id }
        if (urun == null) { js("window.onDestek && onDestek('hata')"); return }
        val params = BillingFlowParams.newBuilder()
            .setProductDetailsParamsList(listOf(
                BillingFlowParams.ProductDetailsParams.newBuilder().setProductDetails(urun).build()
            ))
            .build()
        istemci.launchBillingFlow(etkinlik, params)
    }

    /** Google Play ödeme ekranından dönüş */
    override fun onPurchasesUpdated(sonuc: BillingResult, alimlar: MutableList<Purchase>?) {
        when (sonuc.responseCode) {
            BillingClient.BillingResponseCode.OK -> alimlar?.forEach { tamamla(it, bildir = true) }
            BillingClient.BillingResponseCode.USER_CANCELED -> js("window.onDestek && onDestek('iptal')")
            else -> js("window.onDestek && onDestek('hata')")
        }
    }

    /** Ödemeyi tamamla ve ürünü tüket (tekrar destek olunabilsin) */
    private fun tamamla(alim: Purchase, bildir: Boolean) {
        when (alim.purchaseState) {
            Purchase.PurchaseState.PURCHASED -> {
                val p = ConsumeParams.newBuilder().setPurchaseToken(alim.purchaseToken).build()
                istemci.consumeAsync(p) { r, _ ->
                    if (bildir) js(if (r.responseCode == BillingClient.BillingResponseCode.OK)
                        "window.onDestek && onDestek('ok')" else "window.onDestek && onDestek('hata')")
                }
            }
            Purchase.PurchaseState.PENDING -> if (bildir) js("window.onDestek && onDestek('bekliyor')")
            else -> { }
        }
    }

    /** Uygulama kapalıyken tamamlanmış (ör. sonradan onaylanan) ödemeleri sonuçlandır */
    private fun eskileriTamamla() {
        istemci.queryPurchasesAsync(
            QueryPurchasesParams.newBuilder().setProductType(BillingClient.ProductType.INAPP).build()
        ) { _, liste -> liste.forEach { tamamla(it, bildir = false) } }
    }

    @Suppress("unused")
    private fun onayla(alim: Purchase) {
        // Tüketilen ürünlerde gerekmez; ileride tüketilmeyen ürün eklenirse kullanılır
        istemci.acknowledgePurchase(
            AcknowledgePurchaseParams.newBuilder().setPurchaseToken(alim.purchaseToken).build()
        ) { }
    }
}
