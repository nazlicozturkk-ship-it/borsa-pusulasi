/* Borsa Pusulası - tarayıcı tarafı
   1) Üstteki arama kutusu (yazdıkça öneri)
   2) Fiyat grafikleri (Plotly)
   3) Şirketler tablosu: arama, filtre, sıralama */

const css = (ad) => getComputedStyle(document.documentElement).getPropertyValue(ad).trim();
// Grafiklerde fareyle üzerine gelince çıkan kutunun renkleri
const HOVER = () => ({ bgcolor: css("--panel"), bordercolor: css("--altin"), font: { color: css("--murekkep"), family: "Manrope, sans-serif" } });
const trSayi = (x, b = 2) => x.toLocaleString("tr-TR", { minimumFractionDigits: b, maximumFractionDigits: b });
// Arama için sadeleştirme: büyük harf ve noktasız I ("is" -> ISCTR ve "İŞ BANKASI" ile eşleşir)
const trBuyuk = (s) => s.replace(/İ/g, "I").replace(/ı/g, "i").toUpperCase();

/* ---------------- 1) Arama ---------------- */
(function aramaKur() {
  const kutu = document.getElementById("arama-kutusu");
  const liste = document.getElementById("arama-sonuc");
  if (!kutu) return;
  let zamanlayici, secili = -1, sonuclar = [];

  function goster() {
    liste.innerHTML = "";
    if (!sonuclar.length) {
      liste.hidden = kutu.value.trim() === "";
      if (!liste.hidden) liste.innerHTML = '<li class="yok">Eşleşen şirket yok</li>';
      return;
    }
    sonuclar.forEach((s, i) => {
      const li = document.createElement("li");
      li.innerHTML = `<a href="/sirket/${s.kod}"><b>${s.kod}</b><span>${s.unvan}</span></a>`;
      if (i === secili) li.classList.add("secili");
      liste.appendChild(li);
    });
    liste.hidden = false;
  }

  kutu.addEventListener("input", () => {
    clearTimeout(zamanlayici);
    zamanlayici = setTimeout(async () => {
      const q = kutu.value.trim();
      sonuclar = q ? await (await fetch(`/api/ara?q=${encodeURIComponent(q)}`)).json() : [];
      secili = sonuclar.length ? 0 : -1;
      goster();
    }, 150);
  });
  kutu.addEventListener("keydown", (e) => {
    if (e.key === "ArrowDown") { secili = Math.min(secili + 1, sonuclar.length - 1); goster(); e.preventDefault(); }
    else if (e.key === "ArrowUp") { secili = Math.max(secili - 1, 0); goster(); e.preventDefault(); }
    else if (e.key === "Enter" && sonuclar[secili]) { location.href = `/sirket/${sonuclar[secili].kod}`; }
    else if (e.key === "Escape") { liste.hidden = true; }
  });
  document.addEventListener("click", (e) => { if (!e.target.closest(".arama")) liste.hidden = true; });
})();

/* ---------------- 2) Grafikler ---------------- */
function donemBaslangici(sonTarih, donem) {
  const d = new Date(sonTarih);
  const ay = { "1a": 1, "3a": 3, "6a": 6 }[donem];
  const yil = { "1y": 1, "5y": 5, "10y": 10 }[donem];
  if (ay) d.setMonth(d.getMonth() - ay);
  else if (yil) d.setFullYear(d.getFullYear() - yil);
  else if (donem === "ytd") return `${d.getFullYear() - 1}-12-31`;
  return d.toISOString().slice(0, 10);
}

async function grafikKur(id, ayar = {}) {
  const kutu = document.getElementById(id);
  const kod = kutu.dataset.kod;
  let veri;
  try {
    veri = await (await fetch(`/api/fiyat/${kod}`)).json();
  } catch {
    kutu.innerHTML = '<p class="bos-sonuc">Grafik verisi yüklenemedi. Sayfayı yenileyin.</p>';
    return;
  }
  if (typeof Plotly === "undefined") {
    kutu.innerHTML = '<p class="bos-sonuc">Grafik kütüphanesi yüklenemedi. İnternet bağlantınızı kontrol edin.</p>';
    return;
  }
  const kucuk = !!ayar.kucuk;
  const karsilastirKutu = ayar.karsilastir && document.getElementById(ayar.karsilastir);
  const mumKutu = ayar.mum && document.getElementById(ayar.mum);
  let donem = ayar.varsayilan || "1y";

  function ciz() {
    const son = veri.tarih[veri.tarih.length - 1];
    const bas = donemBaslangici(son, donem);
    // Dönem başındaki son işlem gününü de dahil et (getiri hesabıyla aynı başlangıç)
    let i0 = veri.tarih.findIndex((t) => t > bas);
    if (i0 > 0) i0 -= 1;
    if (i0 < 0) i0 = 0;
    const kes = (a) => a.slice(i0);
    const t = kes(veri.tarih), k = kes(veri.kapanis);
    const yukselis = k[k.length - 1] >= k[0];
    const renk = yukselis ? css("--art") : css("--az");
    const karsilastir = karsilastirKutu && karsilastirKutu.checked;
    const mum = mumKutu && mumKutu.checked && !karsilastir;
    const izler = [];

    if (karsilastir) {
      const yuzdeSeri = (a) => a.map((x) => (x / a[0] - 1) * 100);
      const e = veri.endeks;
      let j0 = e.tarih.findIndex((x) => x >= t[0]);
      if (j0 < 0) j0 = 0;
      izler.push({ x: t, y: yuzdeSeri(k), name: kod, type: "scatter", mode: "lines", line: { color: css("--vurgu"), width: 2 },
                   hovertemplate: `${kod}: %{y:.1f}%<extra></extra>` });
      izler.push({ x: e.tarih.slice(j0), y: yuzdeSeri(e.kapanis.slice(j0)), name: "BIST 100", type: "scatter", mode: "lines",
                   line: { color: css("--soluk"), width: 1.5, dash: "dot" }, hovertemplate: "BIST 100: %{y:.1f}%<extra></extra>" });
    } else if (mum) {
      izler.push({ x: t, open: kes(veri.acilis), high: kes(veri.yuksek), low: kes(veri.dusuk), close: k, type: "candlestick",
                   name: kod, increasing: { line: { color: css("--art") } }, decreasing: { line: { color: css("--az") } } });
    } else {
      izler.push({ x: t, y: k, type: "scatter", mode: "lines", name: kod, line: { color: renk, width: 2 },
                   fill: kucuk ? "none" : "tozeroy", fillcolor: renk + "12",
                   hovertemplate: "%{x|%d.%m.%Y}<br><b>%{y:,.2f}</b><extra></extra>" });
    }
    if (!kucuk && !karsilastir) {
      izler.push({ x: t, y: kes(veri.hacim), type: "bar", yaxis: "y2", name: "Hacim", marker: { color: css("--hacim") },
                   hovertemplate: "Hacim: %{y:,.0f}<extra></extra>" });
    }

    const uzun = ["5y", "10y"].includes(donem);
    const orta = ["1y", "ytd"].includes(donem);
    // Fiyat ekseni sıfırdan değil, dönemdeki en düşük-en yüksek fiyat aralığından başlasın
    const altF = Math.min(...(mum ? kes(veri.dusuk) : k)), ustF = Math.max(...(mum ? kes(veri.yuksek) : k));
    const pay = (ustF - altF) * 0.06 || ustF * 0.05;
    const fiyatBicimi = ustF >= 100 ? ",.0f" : ",.2f";
    const yerlesim = {
      margin: { l: 48, r: 12, t: 8, b: 28 },
      paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "rgba(0,0,0,0)",
      font: { family: "Manrope, sans-serif", size: 12, color: css("--soluk") },
      hoverlabel: HOVER(),
      separators: ",.",
      showlegend: karsilastir, legend: { orientation: "h", x: 0, y: 1.08 },
      hovermode: "x unified",
      xaxis: { type: "date", tickformat: uzun ? "%Y" : orta ? "%m.%Y" : "%d.%m", hoverformat: "%d.%m.%Y", showgrid: false,
               dtick: uzun ? "M12" : orta ? "M2" : undefined,
               rangeslider: { visible: false }, rangebreaks: mum ? [{ bounds: ["sat", "mon"] }] : [] },
      yaxis: { gridcolor: css("--cizgi"), zeroline: false, ticksuffix: karsilastir ? "%" : "",
               tickformat: karsilastir ? ",.0f" : fiyatBicimi,
               range: karsilastir ? undefined : [altF - pay, ustF + pay],
               domain: (!kucuk && !karsilastir) ? [0.22, 1] : [0, 1], fixedrange: true },
      yaxis2: { domain: [0, 0.16], showgrid: false, showticklabels: false, fixedrange: true },
    };
    Plotly.react(kutu, izler, yerlesim, { displayModeBar: false, responsive: true });
  }

  document.querySelectorAll(`.aralik[data-grafik="${id}"] button`).forEach((b) => {
    b.addEventListener("click", () => {
      donem = b.dataset.donem;
      b.parentElement.querySelectorAll("button").forEach((x) => x.setAttribute("aria-pressed", x === b));
      ciz();
    });
  });
  [karsilastirKutu, mumKutu].forEach((k) => k && k.addEventListener("change", () => {
    const not = document.getElementById("karsilastir-not");
    if (not) not.hidden = !karsilastirKutu.checked;
    ciz();
  }));
  ciz();
}

/* ---------------- 3) Şirketler tablosu ---------------- */
function tabloKur() {
  const tablo = document.getElementById("hisse-tablo");
  const govde = tablo.tBodies[0];
  const satirlar = [...govde.rows];
  const ara = document.getElementById("f-ara");
  const sektor = document.getElementById("f-sektor");
  const endeks = document.getElementById("f-endeks");
  const sayac = document.getElementById("sayac");
  const yok = document.getElementById("sonuc-yok");

  // Adres çubuğundan gelen filtre (örn. şirket sayfasındaki sektör bağlantısı)
  const p = new URLSearchParams(location.search);
  if (p.get("sektor")) sektor.value = p.get("sektor");

  satirlar.forEach((r) => (r._ara = trBuyuk(r.dataset.kod + " " + r.dataset.ad)));

  function filtrele() {
    const q = trBuyuk(ara.value.trim());
    let n = 0;
    satirlar.forEach((r) => {
      const gorunur = (!q || r._ara.includes(q)) && (!sektor.value || r.dataset.sektor === sektor.value)
        && (!endeks.value || r.dataset[endeks.value] === "1");
      r.hidden = !gorunur;
      if (gorunur) n++;
    });
    sayac.textContent = `${n} hisse`;
    yok.hidden = n > 0;
  }

  let aktif = null, artan = true;
  tablo.querySelectorAll("[data-sirala]").forEach((b) => {
    b.tabIndex = 0;
    const sirala = () => {
      const alan = b.dataset.sirala;
      artan = aktif === alan ? !artan : alan === "kod";
      aktif = alan;
      tablo.querySelectorAll("[data-sirala]").forEach((x) => x.removeAttribute("aria-sort"));
      b.setAttribute("aria-sort", artan ? "ascending" : "descending");
      const deger = (r) => (alan === "kod" ? r.dataset.kod : parseFloat(r.dataset[alan]));
      satirlar.sort((a, c) => {
        const x = deger(a), y = deger(c);
        if (alan !== "kod") {             // boş değerler her zaman en sonda
          if (isNaN(x)) return 1;
          if (isNaN(y)) return -1;
          return artan ? x - y : y - x;
        }
        return artan ? x.localeCompare(y, "tr") : y.localeCompare(x, "tr");
      });
      satirlar.forEach((r) => govde.appendChild(r));
    };
    b.addEventListener("click", sirala);
    b.addEventListener("keydown", (e) => { if (e.key === "Enter") sirala(); });
  });

  [ara, sektor, endeks].forEach((el) => el.addEventListener("input", filtrele));
  filtrele();
}

/* ---------------- 4) Çoklu grafik (karşılaştırma ve sektör) ----------------
   seriYukle: [{ad, tarih: [...], deger: [...]}, ...] döndüren async fonksiyon.
   Her seri seçilen dönemin başında 0 kabul edilip yüzde değişim olarak çizilir. */
const SERI_RENKLERI = ["--seri0", "--seri1", "--seri2", "--seri3", "--seri4"];

async function cokluGrafikKur(id, seriYukle) {
  const kutu = document.getElementById(id);
  let seriler;
  try {
    seriler = await seriYukle();
  } catch {
    kutu.innerHTML = '<p class="bos-sonuc">Grafik verisi yüklenemedi. Sayfayı yenileyin.</p>';
    return;
  }
  if (typeof Plotly === "undefined") {
    kutu.innerHTML = '<p class="bos-sonuc">Grafik kütüphanesi yüklenemedi.</p>';
    return;
  }
  let donem = "1y";
  const sonTarih = seriler.map((s) => s.tarih[s.tarih.length - 1]).sort().pop();

  function ciz() {
    const bas = donemBaslangici(sonTarih, donem);
    let renkSirasi = 0;
    const izler = seriler.map((s) => {
      let i0 = s.tarih.findIndex((t) => t > bas);
      if (i0 > 0) i0 -= 1;
      if (i0 < 0) return null;            // seçilen dönemde verisi yok
      const t = s.tarih.slice(i0), d = s.deger.slice(i0);
      const endeksMi = s.ad === "BIST 100" || s.ad.startsWith("Tüm hisseler");
      const renk = endeksMi ? css("--soluk") : css(SERI_RENKLERI[renkSirasi++ % 5]);
      return {
        x: t, y: d.map((x) => (x / d[0] - 1) * 100), name: s.ad, type: "scatter", mode: "lines",
        line: { color: renk, width: endeksMi ? 1.5 : 2.2, dash: s.ad === "BIST 100" ? "dot" : endeksMi ? "dash" : "solid" },
        hovertemplate: `${s.ad}: %{y:,.1f}%<extra></extra>`,
      };
    }).filter(Boolean);
    const uzun = ["5y", "10y"].includes(donem), orta = ["1y", "ytd"].includes(donem);
    Plotly.react(kutu, izler, {
      margin: { l: 52, r: 12, t: 8, b: 28 },
      paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "rgba(0,0,0,0)",
      font: { family: "Manrope, sans-serif", size: 12, color: css("--soluk") },
      hoverlabel: HOVER(),
      separators: ",.", hovermode: "x unified",
      legend: { orientation: "h", x: 0, y: 1.1 },
      xaxis: { type: "date", tickformat: uzun ? "%Y" : orta ? "%m.%Y" : "%d.%m", hoverformat: "%d.%m.%Y",
               dtick: uzun ? "M12" : orta ? "M2" : undefined, showgrid: false },
      yaxis: { gridcolor: css("--cizgi"), ticksuffix: "%", tickformat: ",.0f", zeroline: true,
               zerolinecolor: css("--soluk"), zerolinewidth: 1, fixedrange: true },
    }, { displayModeBar: false, responsive: true });
  }

  document.querySelectorAll(`.aralik[data-grafik="${id}"] button`).forEach((b) => {
    b.addEventListener("click", () => {
      donem = b.dataset.donem;
      b.parentElement.querySelectorAll("button").forEach((x) => x.setAttribute("aria-pressed", x === b));
      ciz();
    });
  });
  ciz();
}

/* ---------------- 5) Karşılaştırma: hisse ekleme/çıkarma ---------------- */
function karsilastirmaSeciciKur() {
  const form = document.getElementById("secici");
  const mevcut = () => [...form.querySelectorAll('input[name="k"]')].map((i) => i.value);
  const git = (kodlar) => { location.href = kodlar.length ? `/karsilastir?k=${kodlar.join(",")}` : "/karsilastir"; };

  form.querySelectorAll("[data-kaldir]").forEach((b) =>
    b.addEventListener("click", () => git(mevcut().filter((k) => k !== b.dataset.kaldir))));

  const kutu = document.getElementById("ekle-kutusu");
  const liste = document.getElementById("ekle-sonuc");
  if (!kutu) return;
  let zamanlayici, sonuclar = [], secili = 0;
  const goster = () => {
    liste.innerHTML = sonuclar.length
      ? sonuclar.map((s, i) => `<li class="${i === secili ? "secili" : ""}"><a href="#" data-kod="${s.kod}"><b>${s.kod}</b><span>${s.unvan}</span></a></li>`).join("")
      : '<li class="yok">Eşleşen şirket yok</li>';
    liste.hidden = kutu.value.trim() === "";
  };
  const ekle = (kod) => { if (!mevcut().includes(kod)) git([...mevcut(), kod]); };
  kutu.addEventListener("input", () => {
    clearTimeout(zamanlayici);
    zamanlayici = setTimeout(async () => {
      const q = kutu.value.trim();
      sonuclar = q ? (await (await fetch(`/api/ara?q=${encodeURIComponent(q)}`)).json()).filter((s) => !mevcut().includes(s.kod)) : [];
      secili = 0;
      goster();
    }, 150);
  });
  kutu.addEventListener("keydown", (e) => {
    if (e.key === "ArrowDown") { secili = Math.min(secili + 1, sonuclar.length - 1); goster(); e.preventDefault(); }
    else if (e.key === "ArrowUp") { secili = Math.max(secili - 1, 0); goster(); e.preventDefault(); }
    else if (e.key === "Enter") { e.preventDefault(); if (sonuclar[secili]) ekle(sonuclar[secili].kod); }
    else if (e.key === "Escape") { liste.hidden = true; }
  });
  liste.addEventListener("click", (e) => {
    const a = e.target.closest("a[data-kod]");
    if (a) { e.preventDefault(); ekle(a.dataset.kod); }
  });
  form.addEventListener("submit", (e) => e.preventDefault());
}

/* ---------------- 6) Risk-getiri haritası ---------------- */
function haritaKur(id, noktalar, ayar) {
  const kutu = document.getElementById(id);
  if (typeof Plotly === "undefined") {
    kutu.innerHTML = '<p class="bos-sonuc">Grafik kütüphanesi yüklenemedi.</p>';
    return;
  }
  const secim = document.getElementById("harita-sektor");

  function ciz() {
    const s = secim.value;
    const vurgulu = (n) => (s === "__bist100" ? n.bist100 : n.sektor === s);
    const iz = (liste, renk, boyut, ad, opak) => ({
      x: liste.map((n) => n.x), y: liste.map((n) => n.y),
      customdata: liste.map((n) => [n.kod, n.unvan, n.sektor]),
      type: "scattergl", mode: "markers", name: ad,
      marker: { color: renk, size: boyut, opacity: opak, line: { width: 0 } },
      hovertemplate: `<b>%{customdata[0]}</b> %{customdata[1]}<br>%{customdata[2]}<br>`
        + `${ayar.donemAdi} getiri: %{y:,.1f}%<br>Oynaklık: %{x:,.1f}%<extra></extra>`,
    });
    const izler = s
      ? [iz(noktalar.filter((n) => !vurgulu(n)), css("--nokta"), 6, "Diğer", 0.9),
         iz(noktalar.filter(vurgulu), css("--altin"), 10, secim.selectedOptions[0].text, 0.95)]
      : [iz(noktalar, css("--vurgu"), 7, "Hisseler", 0.55)];
    const cizgi = { type: "line", line: { color: css("--soluk"), width: 1, dash: "dash" }, layer: "below" };
    Plotly.react(kutu, izler, {
      margin: { l: 56, r: 16, t: 16, b: 48 },
      paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "rgba(0,0,0,0)",
      font: { family: "Manrope, sans-serif", size: 12, color: css("--soluk") },
      hoverlabel: HOVER(),
      separators: ",.", showlegend: !!s, legend: { orientation: "h", x: 0, y: 1.06 },
      hovermode: "closest",
      xaxis: { title: { text: "Oynaklık (son 1 yıl, yıllık)" }, ticksuffix: "%", gridcolor: css("--cizgi"), zeroline: false },
      yaxis: { title: { text: `Getiri (${ayar.donemAdi})` }, ticksuffix: "%", tickformat: ",.0f", gridcolor: css("--cizgi"), zeroline: false },
      shapes: [
        { ...cizgi, x0: ayar.endeksX, x1: ayar.endeksX, xref: "x", y0: 0, y1: 1, yref: "paper" },
        { ...cizgi, y0: ayar.endeksY, y1: ayar.endeksY, yref: "y", x0: 0, x1: 1, xref: "paper" },
      ],
      annotations: [{ x: ayar.endeksX, y: ayar.endeksY, text: "BIST 100", showarrow: true, arrowhead: 0, ax: 30, ay: -24,
                      font: { color: css("--murekkep"), size: 12 } }],
    }, { displayModeBar: false, responsive: true });
  }
  secim.addEventListener("change", ciz);
  ciz();
  kutu.on("plotly_click", (e) => {
    const p = e.points && e.points[0];
    if (p && p.customdata) location.href = `/sirket/${p.customdata[0]}`;
  });
}

/* ---------------- 7) Ana sayfa dönem sekmeleri ----------------
   Bütün dönemlerin listeleri sayfada hazırdır; düğmeye basınca sadece ilgili panel
   gösterilir. Adres çubuğu da güncellenir (sayfa yenilenmez), böylece bağlantı
   paylaşıldığında aynı dönem açılır. Ok tuşlarıyla da sekmeler arasında gezilebilir. */
function donemSekmeleriKur() {
  const kap = document.getElementById("donem-sekmeleri");
  if (!kap) return;
  const sekmeler = [...kap.querySelectorAll('[role="tab"]')];
  const sec = (b, odakla) => {
    sekmeler.forEach((x) => {
      const secili = x === b;
      x.setAttribute("aria-selected", secili);
      x.tabIndex = secili ? 0 : -1;
      document.getElementById(x.getAttribute("aria-controls")).hidden = !secili;
    });
    if (odakla) b.focus();
    try { history.replaceState(null, "", `?donem=${b.dataset.donem}`); } catch (e) {}
  };
  sekmeler.forEach((b, i) => {
    b.addEventListener("click", () => sec(b));
    b.addEventListener("keydown", (e) => {
      if (e.key === "ArrowRight") sec(sekmeler[(i + 1) % sekmeler.length], true);
      if (e.key === "ArrowLeft") sec(sekmeler[(i - 1 + sekmeler.length) % sekmeler.length], true);
    });
  });
}

/* ---------------- 8) Tahmin grafiği ----------------
   Son ~6 ayın kapanışları ve her modelin 20 günlük tahmini. En iyi model kalın çizgi ve
   %95 güven aralığı bandıyla, diğer modeller kesikli ince çizgiyle gösterilir.
   Tahmin çizgileri bugünkü kapanıştan başlar ki geçmişle birleşik görünsün. */

async function tahminGrafikKur(id) {
  const kutu = document.getElementById(id);
  if (!kutu) return;
  let v;
  try {
    v = await (await fetch(`/api/tahmin/${kutu.dataset.kod}`)).json();
  } catch {
    kutu.innerHTML = '<p class="bos-sonuc">Tahmin verisi yüklenemedi. Sayfayı yenileyin.</p>';
    return;
  }
  if (typeof Plotly === "undefined") {
    kutu.innerHTML = '<p class="bos-sonuc">Grafik kütüphanesi yüklenemedi.</p>';
    return;
  }
  const sonT = v.gecmis.tarih[v.gecmis.tarih.length - 1];
  const sonF = v.gecmis.kapanis[v.gecmis.kapanis.length - 1];
  const izler = [{
    x: v.gecmis.tarih, y: v.gecmis.kapanis, name: "Gerçekleşen", type: "scatter", mode: "lines",
    line: { color: css("--murekkep"), width: 1.8 }, hovertemplate: "Kapanış: %{y:,.2f}<extra></extra>",
  }];
  const enIyi = v.modeller.find((m) => m.en_iyi);
  if (enIyi && enIyi.alt && enIyi.ust) {
    const t = [sonT, ...enIyi.tarih];
    const bant = css("--altin");
    izler.push({ x: t, y: [sonF, ...enIyi.ust], type: "scatter", mode: "lines", line: { width: 0 },
                 hoverinfo: "skip", showlegend: false });
    izler.push({ x: t, y: [sonF, ...enIyi.alt], type: "scatter", mode: "lines", line: { width: 0 },
                 fill: "tonexty", fillcolor: bant + "22", name: "%95 aralık", hoverinfo: "skip" });
  }
  // Sadece kullanılan (geçmişte en isabetli) modelin tahmini çizilir
  if (enIyi) {
    izler.push({
      x: [sonT, ...enIyi.tarih], y: [sonF, ...enIyi.tahmin], name: "Tahmin",
      type: "scatter", mode: "lines", line: { color: css("--altin"), width: 3 },
      hovertemplate: "Tahmin: %{y:,.2f}<extra></extra>",
    });
  }
  const tumDegerler = izler.flatMap((i) => i.y).filter((x) => Number.isFinite(x));
  const alt = Math.min(...tumDegerler), ust = Math.max(...tumDegerler), pay = (ust - alt) * 0.05;
  Plotly.react(kutu, izler, {
    margin: { l: 52, r: 12, t: 8, b: 28 },
    paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "rgba(0,0,0,0)",
    font: { family: "Manrope, sans-serif", size: 12, color: css("--soluk") },
    hoverlabel: HOVER(), separators: ",.", hovermode: "x unified",
    legend: { orientation: "h", x: 0, y: 1.12, traceorder: "normal" },
    xaxis: { type: "date", tickformat: "%d.%m", hoverformat: "%d.%m.%Y", showgrid: false },
    yaxis: { gridcolor: css("--cizgi"), tickformat: ust >= 100 ? ",.0f" : ",.2f", range: [alt - pay, ust + pay], fixedrange: true },
    shapes: [{ type: "line", x0: sonT, x1: sonT, xref: "x", y0: 0, y1: 1, yref: "paper",
               line: { color: css("--soluk"), width: 1, dash: "dash" } }],
    annotations: [{ x: sonT, y: 1, xref: "x", yref: "paper", text: "bugün", showarrow: false,
                    xanchor: "right", yanchor: "top", font: { size: 11, color: css("--soluk") } }],
  }, { displayModeBar: false, responsive: true });
}

/* ---------------- 9) Yazdırma ----------------
   Grafikler ekran genişliğine göre çizilir; A4 sayfası daha dardır. Yazdırmadan hemen
   önce grafikler sayfa genişliğine küçültülür, yazdırma bitince eski haline döner. */
window.addEventListener("beforeprint", () => {
  if (typeof Plotly === "undefined") return;
  document.querySelectorAll(".js-plotly-plot").forEach((g) => {
    Plotly.relayout(g, { width: 690, height: g.classList.contains("grafik-tahmin") ? 300 : 230 });
  });
});
window.addEventListener("afterprint", () => {
  if (typeof Plotly === "undefined") return;
  document.querySelectorAll(".js-plotly-plot").forEach((g) => {
    Plotly.relayout(g, { width: null, height: null, autosize: true });
  });
});
