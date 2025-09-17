# Tahsilat - Ödeme Raporlama Otomasyonu

Bu uygulama, emlak geliştirme şirketleri için günlük ve aylık ödeme raporlarını otomatik olarak oluşturan masaüstü uygulamasıdır.

## 🚀 Özellikler

### 📊 Veri İçe Aktarma
- **CSV, XLSX, JSON** dosya formatlarını destekler
- Manuel tablo girişi (Excel benzeri grid)
- Otomatik veri doğrulama ve hata kontrolü
- Çoklu sayfa desteği (XLSX için)

### 💱 Döviz Dönüştürme
- **TCMB** resmi döviz kurlarından otomatik TL→USD dönüştürme
- Ödeme tarihinden **bir gün önceki** kur kullanımı
- Yerel JSON önbellekleme ile performans optimizasyonu
- Manuel kur girişi desteği

### 💾 Yerel Depolama
- Tüm veriler **JSON** formatında yerel olarak saklanır
- Günlük yedekleme (snapshot) sistemi
- Veri geri yükleme ve yedekleme yönetimi
- Otomatik veri temizleme

### 📈 Rapor Oluşturma
- **Günlük USD dağılımı** (müşteri ve proje bazında)
- **Haftalık özet** (proje bazında)
- **Aylık kanal dağılımı** (proje ve ödeme kanalı bazında)
- **Günlük zaman çizelgesi** (ay içi günlük toplamlar)
- **Ödeme türü özeti** (TL ve USD toplamları)

### 📄 Çıktı Formatları
- **Excel (.xlsx)** - Tek sayfa, formatlanmış tablolar
- **PDF** - Profesyonel rapor formatı
- **Word (.docx)** - Düzenlenebilir belge formatı

### 🎯 Akıllı Algılama
- Ödeme kanalı otomatik tespiti ("Hesap Adı"ndan)
- Proje adı otomatik gruplama
- Döviz türü ve dönüştürme ihtiyacı algılama
- Ödeme türü kategorilendirme

## 🛠️ Kurulum

### Gereksinimler
- Python 3.11+
- Windows 10/11 (test edildi)

### Adımlar
1. **Bağımlılıkları yükleyin:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Uygulamayı çalıştırın:**
   ```bash
   python main.py
   ```

## 📖 Kullanım

### 1. Veri İçe Aktarma
- **Dosya Seç** butonuna tıklayın
- CSV, XLSX veya JSON dosyası seçin
- Dosya formatını seçin (otomatik algılanır)
- XLSX için sayfa seçin (gerekirse)
- **İçe Aktar** butonuna tıklayın

### 2. Manuel Veri Girişi
- **Manuel Giriş** sekmesine geçin
- Tabloya veri girin
- **Satır Ekle** ile yeni satır ekleyin
- Veriler otomatik olarak kaydedilir

### 3. Rapor Oluşturma
- Tarih aralığını seçin
- İstediğiniz rapor türünü seçin:
  - **Günlük Rapor** - Müşteri ve proje bazında günlük dağılım
  - **Haftalık Rapor** - Proje bazında haftalık özet
  - **Aylık Rapor** - Kanal ve proje bazında aylık dağılım
  - **Tüm Raporlar** - Tüm formatlarda (Excel, PDF, Word)

### 4. Veri Yönetimi
- **Yenile** - Verileri yeniden yükle
- **Dışa Aktar** - Verileri JSON/CSV olarak kaydet
- **Günlük Yedekleme** - Anlık yedek oluştur

## 📊 Örnek Rapor Formatları

### Günlük USD Dağılımı
| Müşteri | Proje | Pazartesi | Salı | ... | Genel Toplam |
|---------|-------|-----------|------|-----|--------------|
| Musa Özdoğan | MSM | $8,502 | | | $8,502 |

### Aylık Kanal Dağılımı
| Kanal | PROJECT_A USD | MSM USD |
|-------|---------|---------|
| ÇARŞI | $296,556 | |
| KUYUMCUKENT | $110,735 | |
| OFİS | $15,000 | $8,501 |

## 🔧 Teknik Detaylar

### Proje Yapısı
```
tahsilat/
├── main.py              # Ana uygulama giriş noktası
├── ui_main.py           # PySide6 GUI uygulaması
├── data_import.py       # Veri içe aktarma modülü
├── currency.py          # TCMB döviz kuru modülü
├── storage.py           # JSON yerel depolama
├── report_generator.py  # Rapor oluşturma modülü
├── requirements.txt     # Python bağımlılıkları
├── sample_data.csv      # Örnek CSV verisi
├── sample_data.json     # Örnek JSON verisi
└── README.md           # Bu dosya
```

### Desteklenen Veri Alanları
- **Müşteri Adı Soyadı** - Müşteri bilgisi
- **Tarih** - Ödeme tarihi (çeşitli formatlar)
- **Proje Adı** - Proje bilgisi
- **Hesap Adı** - Ödeme kanalı tespiti için
- **Ödenen Tutar** - Ödeme miktarı
- **Ödenen Döviz** - Para birimi (TL/USD)
- **Ödenen Kur** - Döviz kuru (manuel giriş)
- **Ödeme Durumu** - Ödeme durumu

### Döviz Kuru Entegrasyonu
- **TCMB XML API** kullanımı
- Günlük otomatik kur çekme
- Yerel JSON önbellekleme
- Hata durumunda manuel kur girişi

## 🐛 Hata Giderme

### Yaygın Sorunlar
1. **Dosya okunamıyor** - Dosya formatını kontrol edin
2. **Döviz kuru alınamıyor** - İnternet bağlantısını kontrol edin
3. **Rapor oluşturulamıyor** - Çıktı klasörü yazma izinlerini kontrol edin

### Log Dosyaları
Uygulama detaylı log kayıtları tutar. Hata durumunda konsol çıktısını kontrol edin.

## 📝 Lisans

Bu proje MIT lisansı altında lisanslanmıştır.

## 🤝 Katkıda Bulunma

1. Fork yapın
2. Feature branch oluşturun (`git checkout -b feature/AmazingFeature`)
3. Commit yapın (`git commit -m 'Add some AmazingFeature'`)
4. Push yapın (`git push origin feature/AmazingFeature`)
5. Pull Request oluşturun

## 📞 Destek

Sorularınız için issue oluşturun veya iletişime geçin.
