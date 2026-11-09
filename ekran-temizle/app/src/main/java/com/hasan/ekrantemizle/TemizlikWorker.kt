package com.hasan.ekrantemizle

import android.content.Context
import android.os.Environment
import androidx.work.Worker
import androidx.work.WorkerParameters

class TemizlikWorker(ctx: Context, params: WorkerParameters) : Worker(ctx, params) {
    override fun doWork(): Result {
        if (Environment.isExternalStorageManager()) {
            Temizleyici.temizle(applicationContext)
        }
        return Result.success()
    }
}
