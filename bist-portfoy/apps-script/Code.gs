/**
 * BIST Portföy Android uygulaması için Google Sheet API'si.
 *
 * Kurulum:
 * 1. Google Sheet'i açın → Uzantılar → Apps Script.
 * 2. Bu dosyanın tamamını Code.gs içine yapıştırın.
 * 3. Aşağıdaki TOKEN değerini kendinize özel uzun bir şifreyle değiştirin.
 * 4. Dağıt → Yeni dağıtım → Tür: Web uygulaması
 *    Yürüten: Ben · Erişimi olanlar: Herkes → Dağıt → izinleri onaylayın.
 * 5. Verilen /exec ile biten URL'yi ve TOKEN'ı uygulamanın Ayarlar ekranına girin.
 */
const TOKEN = 'BURAYA-KENDI-SIFRENIZI-YAZIN';

function doGet(e) {
  const p = (e && e.parameter) || {};
  if (TOKEN === 'BURAYA-KENDI-SIFRENIZI-YAZIN' || p.token !== TOKEN) return out_({ error: 'yetkisiz' });
  const ss = SpreadsheetApp.getActive();
  const sh = ss.getSheetByName('Takip');

  if (p.action === 'write') {
    // Yalnızca hisse kodu (A), sektör (B) ve portföy girdileri (C:H), satır 6–35
    const m = /^([A-H])(\d{1,2})(?::([A-H])\2)?$/.exec(p.range || '');
    const row = m ? Number(m[2]) : 0;
    if (!m || row < 6 || row > 35) return out_({ error: 'gecersiz_aralik' });
    const values = JSON.parse(p.values || '[]');
    const lock = LockService.getScriptLock();
    lock.waitLock(10000);
    try {
      sh.getRange(p.range).setValues(values);
      SpreadsheetApp.flush();
    } finally {
      lock.releaseLock();
    }
  }

  const enf = ss.getSheetByName('Enflasyon').getRange('A4:B99').getValues()
    .filter(r => r[0] instanceof Date && r[1] !== '' && r[1] !== null)
    .map(r => [Utilities.formatDate(r[0], 'Europe/Istanbul', 'yyyy-MM'), Number(r[1])]);

  return out_({
    values: sh.getRange('A3:BN35').getDisplayValues(),
    enflasyon: enf,
    at: new Date().toISOString()
  });
}

function out_(o) {
  return ContentService.createTextOutput(JSON.stringify(o)).setMimeType(ContentService.MimeType.JSON);
}
