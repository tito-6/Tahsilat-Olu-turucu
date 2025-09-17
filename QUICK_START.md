# 🚀 Tahsilat - Hızlı Başlangıç Rehberi

## ✅ Uygulama Hazır!

Tahsilat uygulaması başarıyla kuruldu ve örnek veriler yüklendi.

## 🖥️ Uygulamayı Çalıştırma

```bash
python main.py
```

## 📊 Örnek Veriler Yüklendi

- **20 ödeme kaydı** başarıyla yüklendi
- **2 proje**: Model Sanayi Merkezi, Model Kuyum Merkezi
- **20 müşteri** farklı ödemeler
- **4 ödeme kanalı**: ÇARŞI, KUYUMCUKENT, OFİS, BANKA HAVALESİ
- **Tarih aralığı**: 15 Ocak - 3 Şubat 2024
- **Toplam tutar**: 179,206.50 TL

## 🎯 İlk Rapor Oluşturma

1. **Uygulamayı açın**: `python main.py`
2. **Tarih aralığını ayarlayın**:
   - Başlangıç: 15.01.2024
   - Bitiş: 03.02.2024
3. **Rapor oluşturun**:
   - "Günlük Rapor" - Müşteri ve proje bazında günlük dağılım
   - "Aylık Rapor" - Kanal ve proje bazında aylık dağılım
   - "Tüm Raporlar" - Excel, PDF, Word formatlarında

## 📁 Veri Dosyaları

- `sample_data.csv` - 20 örnek ödeme kaydı
- `sample_data.json` - 10 örnek ödeme kaydı
- `data/payments.json` - Uygulama veri dosyası (otomatik oluşturuldu)

## 🔧 Sorun Giderme

### "Rapor oluşturmak için veri bulunamadı" Hatası

Bu hata şu durumlarda oluşur:

1. **Veri yüklenmemiş**: Önce veri içe aktarın
2. **Tarih aralığı yanlış**: Doğru tarih aralığını seçin
3. **Veri filtrelenmiş**: Tüm verileri görmek için tarih aralığını genişletin

### Çözüm:

1. **Veri yükleme**:
   - "Gözat" butonuna tıklayın
   - `sample_data.csv` dosyasını seçin
   - "İçe Aktar" butonuna tıklayın

2. **Tarih aralığı**:
   - Başlangıç: 15.01.2024
   - Bitiş: 03.02.2024

3. **Veri kontrolü**:
   - "Veri Tablosu" sekmesinde verileri görün
   - Sol panelde istatistikleri kontrol edin

## 📊 Rapor Türleri

### 1. Günlük Rapor
- Müşteri ve proje bazında günlük USD dağılımı
- Her gün için ayrı sütun
- Genel toplam sütunu

### 2. Aylık Rapor
- Proje ve ödeme kanalı bazında aylık dağılım
- Kanal bazında gruplandırma
- Toplam satırı

### 3. Haftalık Rapor
- Proje bazında haftalık özet
- Hafta numaraları ile gruplandırma

### 4. Tüm Raporlar
- Excel (.xlsx) - Düzenlenebilir tablolar
- PDF (.pdf) - Profesyonel rapor formatı
- Word (.docx) - Düzenlenebilir belge

## 💱 Döviz Dönüştürme

- **TL ödemeleri** otomatik olarak USD'ye dönüştürülür
- **TCMB resmi kurları** kullanılır
- **Ödeme tarihinden bir gün önceki** kur uygulanır
- **Yerel önbellekleme** ile performans optimizasyonu

## 🔄 Veri Yönetimi

### Veri İçe Aktarma
- **CSV**: Virgülle ayrılmış değerler
- **XLSX**: Excel dosyaları
- **JSON**: JavaScript Object Notation
- **Manuel**: Tablo arayüzü ile giriş

### Veri Dışa Aktarma
- **JSON**: Uygulama formatı
- **CSV**: Excel ile uyumlu

### Yedekleme
- **Günlük yedekleme**: Otomatik snapshot
- **Manuel yedekleme**: Araçlar menüsünden
- **Geri yükleme**: Snapshot'lardan

## 🎯 Sonraki Adımlar

1. **Kendi verilerinizi yükleyin**
2. **Farklı rapor türlerini deneyin**
3. **Tarih aralıklarını değiştirin**
4. **Çıktı formatlarını test edin**

## 📞 Yardım

- **Hata mesajları**: Konsol çıktısını kontrol edin
- **Log dosyaları**: Detaylı hata bilgileri
- **Test scripti**: `python test_app.py`

---

**🎉 Artık Tahsilat uygulamasını kullanmaya hazırsınız!**
