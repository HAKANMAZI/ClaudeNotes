package com.hasan.donustur

import android.graphics.Bitmap
import android.media.MediaCodec
import android.media.MediaExtractor
import android.media.MediaFormat
import android.media.MediaMetadataRetriever
import android.media.MediaMuxer
import java.io.File
import java.io.RandomAccessFile
import java.nio.ByteBuffer
import java.nio.ByteOrder

/** Ses/video işlemleri: Android'in kendi kodekleriyle, internetsiz. */
object Medya {

    private fun izBul(ex: MediaExtractor, onEk: String): Int {
        for (i in 0 until ex.trackCount) {
            val m = ex.getTrackFormat(i).getString(MediaFormat.KEY_MIME) ?: continue
            if (m.startsWith(onEk)) return i
        }
        return -1
    }

    /** Videonun/sesin AAC iz(ler)ini yeniden kodlamadan .m4a ya da sessiz .mp4 olarak çıkarır. */
    fun izKopyala(girdi: File, cikti: File, sesMi: Boolean) {
        val ex = MediaExtractor()
        ex.setDataSource(girdi.absolutePath)
        val iz = izBul(ex, if (sesMi) "audio/" else "video/")
        if (iz < 0) { ex.release(); throw IllegalStateException(if (sesMi) "Dosyada ses yok" else "Dosyada görüntü yok") }
        val bicim = ex.getTrackFormat(iz)
        val mime = bicim.getString(MediaFormat.KEY_MIME) ?: ""
        if (sesMi && mime != MediaFormat.MIMETYPE_AUDIO_AAC) {
            ex.release()
            throw IllegalStateException("Ses AAC değil ($mime). Bunun yerine WAV seçin.")
        }
        ex.selectTrack(iz)
        val mux = MediaMuxer(cikti.absolutePath, MediaMuxer.OutputFormat.MUXER_OUTPUT_MPEG_4)
        val hedef = mux.addTrack(bicim)
        if (!sesMi && bicim.containsKey(MediaFormat.KEY_ROTATION)) mux.setOrientationHint(bicim.getInteger(MediaFormat.KEY_ROTATION))
        mux.start()
        val boyut = if (bicim.containsKey(MediaFormat.KEY_MAX_INPUT_SIZE)) bicim.getInteger(MediaFormat.KEY_MAX_INPUT_SIZE) else 4 * 1024 * 1024
        val tampon = ByteBuffer.allocate(maxOf(boyut, 1024 * 1024))
        val bilgi = MediaCodec.BufferInfo()
        while (true) {
            val n = ex.readSampleData(tampon, 0)
            if (n < 0) break
            bilgi.offset = 0
            bilgi.size = n
            bilgi.presentationTimeUs = ex.sampleTime
            bilgi.flags = if ((ex.sampleFlags and MediaExtractor.SAMPLE_FLAG_SYNC) != 0) MediaCodec.BUFFER_FLAG_KEY_FRAME else 0
            mux.writeSampleData(hedef, tampon, bilgi)
            ex.advance()
        }
        mux.stop(); mux.release(); ex.release()
    }

    /** MP3, M4A, OGG, FLAC, video… cihazın çözebildiği her sesi 16-bit WAV'a çevirir. */
    fun wav(girdi: File, cikti: File, ilerleme: (Int) -> Unit = {}) {
        val ex = MediaExtractor()
        ex.setDataSource(girdi.absolutePath)
        val iz = izBul(ex, "audio/")
        if (iz < 0) { ex.release(); throw IllegalStateException("Dosyada ses yok") }
        val bicim = ex.getTrackFormat(iz)
        ex.selectTrack(iz)
        val sure = if (bicim.containsKey(MediaFormat.KEY_DURATION)) bicim.getLong(MediaFormat.KEY_DURATION) else 0L
        val kod = MediaCodec.createDecoderByType(bicim.getString(MediaFormat.KEY_MIME)!!)
        kod.configure(bicim, null, null, 0)
        kod.start()
        var ornekHizi = bicim.getInteger(MediaFormat.KEY_SAMPLE_RATE)
        var kanal = bicim.getInteger(MediaFormat.KEY_CHANNEL_COUNT)
        val raf = RandomAccessFile(cikti, "rw")
        raf.setLength(0)
        raf.write(ByteArray(44)) // başlık sonra yazılacak
        var veri = 0L
        val bilgi = MediaCodec.BufferInfo()
        var girisBitti = false
        var bitti = false
        var parca = ByteArray(0)
        while (!bitti) {
            if (!girisBitti) {
                val gi = kod.dequeueInputBuffer(10_000)
                if (gi >= 0) {
                    val buf = kod.getInputBuffer(gi)!!
                    val n = ex.readSampleData(buf, 0)
                    if (n < 0) {
                        kod.queueInputBuffer(gi, 0, 0, 0, MediaCodec.BUFFER_FLAG_END_OF_STREAM)
                        girisBitti = true
                    } else {
                        kod.queueInputBuffer(gi, 0, n, ex.sampleTime, 0)
                        if (sure > 0) ilerleme((ex.sampleTime * 100 / sure).toInt())
                        ex.advance()
                    }
                }
            }
            val ci = kod.dequeueOutputBuffer(bilgi, 10_000)
            if (ci == MediaCodec.INFO_OUTPUT_FORMAT_CHANGED) {
                val f = kod.outputFormat
                ornekHizi = f.getInteger(MediaFormat.KEY_SAMPLE_RATE)
                kanal = f.getInteger(MediaFormat.KEY_CHANNEL_COUNT)
            } else if (ci >= 0) {
                if (bilgi.size > 0) {
                    val buf = kod.getOutputBuffer(ci)!!
                    buf.position(bilgi.offset); buf.limit(bilgi.offset + bilgi.size)
                    if (parca.size < bilgi.size) parca = ByteArray(bilgi.size)
                    buf.get(parca, 0, bilgi.size)
                    raf.write(parca, 0, bilgi.size)
                    veri += bilgi.size
                }
                kod.releaseOutputBuffer(ci, false)
                if ((bilgi.flags and MediaCodec.BUFFER_FLAG_END_OF_STREAM) != 0) bitti = true
            }
        }
        kod.stop(); kod.release(); ex.release()
        // WAV başlığı
        val b = ByteBuffer.allocate(44).order(ByteOrder.LITTLE_ENDIAN)
        b.put("RIFF".toByteArray()); b.putInt((36 + veri).toInt()); b.put("WAVE".toByteArray())
        b.put("fmt ".toByteArray()); b.putInt(16); b.putShort(1); b.putShort(kanal.toShort())
        b.putInt(ornekHizi); b.putInt(ornekHizi * kanal * 2); b.putShort((kanal * 2).toShort()); b.putShort(16)
        b.put("data".toByteArray()); b.putInt(veri.toInt())
        raf.seek(0); raf.write(b.array()); raf.close()
    }

    /** Videodan kareler (başta, ortada, sonda) — JPG kapak/önizleme. */
    fun kareler(girdi: File, adet: Int = 1): List<Bitmap> {
        val r = MediaMetadataRetriever()
        r.setDataSource(girdi.absolutePath)
        val sure = (r.extractMetadata(MediaMetadataRetriever.METADATA_KEY_DURATION)?.toLongOrNull() ?: 0L) * 1000
        val liste = mutableListOf<Bitmap>()
        for (i in 0 until adet) {
            val t = if (adet == 1) minOf(1_000_000L, sure / 2) else sure * (i + 1) / (adet + 1)
            r.getFrameAtTime(t, MediaMetadataRetriever.OPTION_CLOSEST_SYNC)?.let { liste.add(it) }
        }
        r.release()
        if (liste.isEmpty()) throw IllegalStateException("Videodan kare alınamadı")
        return liste
    }
}
