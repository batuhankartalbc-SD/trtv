"""Ayarlar, profiller ve kalıcı depolama."""
from __future__ import annotations

import json
import os
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path

# İki ortam: CANLI (kurulu uygulama) ve GELİŞTİRME (kaynak koddan, TRCEVIRI_DEV=1).
# Geliştirme ortamı ayarlarını/önbelleğini ayrı klasörde tutar; canlı uygulamaya dokunmaz.
DEV = os.environ.get("TRCEVIRI_DEV") == "1"
APP_DIR = Path(os.environ.get("APPDATA", Path.home())) / ("TRCeviri-Dev" if DEV else "TRCeviri")
PROFILE_DIR = APP_DIR / "profiles"
LOG_DIR = APP_DIR / "logs"
CONFIG_FILE = APP_DIR / "config.json"
CACHE_FILE = APP_DIR / "cache.sqlite"
BUNDLED_PROFILES = Path(__file__).resolve().parent.parent / "profiles"

ZONE_TYPES = {
    "subtitle": "Diyalog altyazısı",
    "objective": "Görev yazısı",
    "phone": "Telefon / mesaj",
    "help": "İpucu kutusu",
    "menu": "Menü",
    "free": "Serbest alan",
}
# Düşük sayı = yüksek öncelik
ZONE_PRIORITY = {"subtitle": 0, "objective": 1, "help": 2, "phone": 2, "free": 3, "menu": 4}
# Bu türlerde bölgedeki tüm satırlar tek blok olarak çevrilir; diğerlerinde satır satır.
BLOCK_TYPES = {"subtitle", "objective"}


@dataclass
class Zone:
    name: str = "Yeni bölge"
    type: str = "free"
    x: float = 0.1
    y: float = 0.1
    w: float = 0.3
    h: float = 0.1
    enabled: bool = True
    min_confidence: float = 0.6
    font_scale: float = 1.0
    stability_ms: int = 120               # bölge modunda yazının sabit kalması gereken süre
    align: str = "c"                      # c = ortalı, l = sola dayalı, r = sağa dayalı
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])

    @staticmethod
    def from_dict(d: dict) -> "Zone":
        z = Zone()
        for k, v in d.items():
            if hasattr(z, k):
                setattr(z, k, v)
        return z


@dataclass
class Profile:
    name: str = "Genel"
    game: str = ""
    zones: list[Zone] = field(default_factory=list)
    glossary: dict[str, str] = field(default_factory=dict)  # boş değer = çevirme
    ignore: list[str] = field(default_factory=list)          # tam eşleşen satırlar atlanır
    style: str = ""                                           # LLM için oyun/karakter üslup talimatı
    pack: str = ""                                            # hazır çeviri paketi (profiles/packs/<pack>.json)
    speaker_colors: dict[str, str] = field(default_factory=dict)   # konuşmacı adı → renk
    kind: str = "game"                                        # game (oyun) | film (film/dizi: sadece alttaki altyazı)
    window_hint: str = ""                                     # boş değilse bu profil seçilince okunacak pencere (ör. VLC)

    @property
    def is_film(self) -> bool:
        return self.kind == "film"

    def to_dict(self) -> dict:
        d = asdict(self)
        return d

    @staticmethod
    def from_dict(d: dict) -> "Profile":
        p = Profile(name=d.get("name", "Genel"), game=d.get("game", ""))
        p.zones = [Zone.from_dict(z) for z in d.get("zones", [])]
        p.glossary = dict(d.get("glossary", {}))
        p.ignore = list(d.get("ignore", []))
        p.style = d.get("style", "")
        p.pack = d.get("pack", "")
        p.speaker_colors = dict(d.get("speaker_colors", {}))
        p.kind = d.get("kind", "game") if d.get("kind") in ("game", "film") else "game"
        p.window_hint = d.get("window_hint", "")
        return p


@dataclass
class Settings:
    window_hint: str = "PS Remote Play"
    force_16_9: bool = True
    capture_mode: str = "auto"            # auto | window | screen
    auto_restore: bool = True             # Remote Play küçültülürse arka planda geri aç (okumaya devam)
    auto_mode: bool = True
    cat_dialogue: bool = True             # konuşmalar / altyazılar
    cat_menu: bool = True                 # menüler
    cat_controls: bool = True             # kontroller / tuş ipuçları
    cat_other: bool = False               # diğer oyun yazıları (tabela, bildirim, görev...)
    cat_nav: bool = False                 # GPS / yön / mesafe ("Turn Right 8 m")
    bg_mode: str = "black"                # yazı arkası: black (simsiyah) | game (oyun rengi) | semi (yarı saydam siyah)
    output_target: str = "both"           # Çevirilerin görüneceği yer: pc | tv | both
    setup_done: bool = False              # kurulum sihirbazı tamamlandı mı
    ocr_threads: int = 4                  # OCR iş parçacığı (işlemci çekirdeği)
    tv_enabled: bool = True               # çevirileri Android TV'deki Brolis Game Translate (TV)'ye gönder
    tv_host: str = ""                     # son bulunan TV adresi (boşsa ağ taranır)
    output_pc: bool = True                # çevirileri bilgisayar ekranında da göster                # tüm ekranı tara, bölge gerekmez
    auto_scan_width: int = 960            # tespit için küçültme genişliği (büyük = küçük yazıları da bulur, yavaş)
    profile: str = "Genel oyun (her oyun)"
    engine: str = "local"                 # local | gemini | openai | claude | deepl | free
    refine: bool = True                   # yerel anlık çeviriden sonra Gemini (anahtar varsa) ile iyileştir
    models: dict[str, str] = field(default_factory=lambda: {
        "gemini": "gemini-3.5-flash-lite",
        "openai": "gpt-4.1-mini",
        "claude": "claude-haiku-5-5",
    })
    api_keys_enc: dict[str, str] = field(default_factory=dict)
    fallback_free: bool = True
    context_lines: int = 6
    tone: str = "samimi"
    fps: int = 30
    instant: bool = True                  # anlık mod: yazı ilk görüldüğü karede çevrilip gösterilir
    change_threshold: float = 3.0
    use_gpu: bool = True                  # yazı tespiti DirectML ile ekran kartında (yoksa kendiliğinden işlemci)
    font_family: str = "Segoe UI Semibold"
    font_scale: float = 1.0               # 1.0 = oyundaki İngilizce yazıyla birebir aynı boyut
    font_choice: str = "default"          # default | condensed | rounded | clean (bkz. fonts.py)
    box_color: str = "#000000"
    box_opacity: int = 250
    display_mode: str = "match"           # match (oyun stili 1:1) | opaque (opak kutu) | semi (yarı saydam) | text (sadece yazı)
    match_colors: bool = True             # oyun stilinde yazı/zemin rengini oyundan ölç
    tv_dx: float = 0.0                    # TV kalibrasyonu: yatay kayma (ekran genişliğinin %'si)
    tv_dy: float = 0.0                    # dikey kayma (%)
    tv_sx: float = 100.0                  # yatay ölçek (%)
    tv_sy: float = 100.0                  # dikey ölçek (%)
    text_color: str = "#FFFFFF"
    speaker_color: str = "#FFD54A"
    show_speaker: bool = True
    speaker_colors_on: bool = True        # her konuşmacıya kendi rengi
    tts_enabled: bool = False             # Türkçe seslendirme (Windows Türkçe sesi)
    tts_rate: float = 1.15                # konuşma hızı
    debug_boxes: bool = False

    def set_output(self, target: str) -> None:
        """pc = sadece bilgisayar, tv = sadece TV, both = ikisi."""
        self.output_target = target
        self.output_pc = target in ("pc", "both")
        self.tv_enabled = target in ("tv", "both")

    def categories(self, film: bool = False) -> set[str]:
        if film:                       # film/dizi: ekrandaki diğer yazılar (oynatıcı düğmeleri vb.) çevrilmez
            return {"subtitle"}
        m = {"subtitle": self.cat_dialogue, "menu": self.cat_menu, "controls": self.cat_controls,
             "other": self.cat_other, "nav": self.cat_nav}
        return {k for k, v in m.items() if v}

    def save(self) -> None:
        APP_DIR.mkdir(parents=True, exist_ok=True)
        tmp = CONFIG_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(asdict(self), ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(CONFIG_FILE)

    @staticmethod
    def load() -> "Settings":
        s = Settings()
        if DEV and not CONFIG_FILE.exists():
            # ilk geliştirme açılışı: canlı ayarları kopyala, ama TV'yi kapalı başlat (canlının TV bağlantısını kapmasın)
            live = Path(os.environ.get("APPDATA", Path.home())) / "TRCeviri"
            try:
                import shutil
                APP_DIR.mkdir(parents=True, exist_ok=True)
                if (live / "config.json").exists():
                    shutil.copy2(live / "config.json", CONFIG_FILE)
                if (live / "profiles").exists() and not PROFILE_DIR.exists():
                    shutil.copytree(live / "profiles", PROFILE_DIR)
                d = json.loads(CONFIG_FILE.read_text(encoding="utf-8")) if CONFIG_FILE.exists() else {}
                d.update({"tv_enabled": False, "output_target": "pc", "output_pc": True, "setup_done": True})
                CONFIG_FILE.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
            except Exception:
                pass
        if CONFIG_FILE.exists():
            try:
                d = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
                for k, v in d.items():
                    if hasattr(s, k):
                        if k == "engine" and v in ("free", "google_free"):
                            v = "local"   # eski kurulumlar: hızlı yerel motora geç
                        if k == "models":
                            s.models.update(v)
                        else:
                            setattr(s, k, v)
                if "match_colors" not in d:      # eski kurulum: yeni varsayılan "oyun stili"
                    s.display_mode = "match"
                if "output_target" not in d:     # eski kurulum: mevcut duruma göre
                    s.output_target = ("both" if s.output_pc else "tv") if s.tv_enabled else "pc"
                    s.setup_done = True          # zaten kullanıyordu; sihirbazı zorla açma
                if "bg_mode" not in d:           # yeni varsayılanlar: simsiyah zemin, birebir boyut
                    s.bg_mode = "black"
                    s.font_scale = 1.0
                    s.box_color = "#000000"
            except Exception:
                pass
        return s


def _profile_path(name: str) -> Path:
    safe = "".join(c if c.isalnum() or c in " -_" else "_" for c in name).strip() or "profil"
    return PROFILE_DIR / f"{safe}.json"


def ensure_bundled_profiles() -> None:
    """Hazır profilleri kullanıcı klasörüne kopyalar; aynı adlı profil zaten varsa (kullanıcı düzenlemiş) dokunmaz."""
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    if BUNDLED_PROFILES.exists():
        have = set()
        for f in PROFILE_DIR.glob("*.json"):
            try:
                have.add(json.loads(f.read_text(encoding="utf-8")).get("name"))
            except Exception:
                pass
        for f in BUNDLED_PROFILES.glob("*.json"):
            try:
                name = json.loads(f.read_text(encoding="utf-8")).get("name")
            except Exception:
                continue
            if name not in have:
                (PROFILE_DIR / f.name).write_text(f.read_text(encoding="utf-8"), encoding="utf-8")
                have.add(name)


def list_profiles() -> list[str]:
    ensure_bundled_profiles()
    names = []
    for f in sorted(PROFILE_DIR.glob("*.json")):
        try:
            names.append(json.loads(f.read_text(encoding="utf-8")).get("name", f.stem))
        except Exception:
            continue
    names = list(dict.fromkeys(names)) or ["Genel"]
    first = [n for n in ("Genel oyun (her oyun)", "Film / dizi") if n in names]
    return first + sorted((n for n in names if n not in first), key=str.casefold)


def load_profile(name: str) -> Profile:
    ensure_bundled_profiles()
    for f in PROFILE_DIR.glob("*.json"):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        if d.get("name") == name:
            return Profile.from_dict(d)
    return Profile(name=name, zones=[Zone(name="Altyazı", type="subtitle", x=0.1, y=0.78, w=0.8, h=0.18)])


def save_profile(p: Profile) -> Path:
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    path = _profile_path(p.name)
    path.write_text(json.dumps(p.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    return path
