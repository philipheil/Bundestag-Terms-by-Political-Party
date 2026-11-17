# Lädt alle Plenarprotokolle (XML) der 19., 20. und 21. Wahlperiode
# von https://www.bundestag.de/services/opendata herunter.
#
# Nutzung in R / RStudio:
#   1. Arbeitsverzeichnis auf den Projektordner setzen, z. B. setwd("pfad/zum/projekt")
#   2. source("download_plenarprotokolle.R")
#
# Mit NUR_LINKS <- TRUE werden nur die Links gesammelt und nichts heruntergeladen.

# ---- Einstellungen ----------------------------------------------------------

ZIELORDNER     <- "Plenarprotokolle"  # relativ zum Arbeitsverzeichnis
DOWNLOAD_PAUSE <- 5                   # Sekunden zwischen zwei Downloads
LISTEN_PAUSE   <- 1                   # Sekunden zwischen zwei Listen-Abfragen
NUR_LINKS      <- FALSE

# Wahlperiode -> ID der Dokumentenliste auf der Open-Data-Seite
WAHLPERIODEN <- c("19" = "543410", "20" = "866354", "21" = "1058442")

LISTEN_URL <- "https://www.bundestag.de/ajax/filterlist/de/services/opendata/%s-%s?limit=10&noFilterSet=true&offset=%d"
LINK_MUSTER <- "https://www\\.bundestag\\.de/resource/blob/[0-9]+/[0-9]+\\.xml"

# Ehrliche Kennung statt eines vorgetäuschten Browsers. Wer das Skript
# veröffentlicht oder im großen Stil nutzt, sollte hier eine Kontaktadresse
# oder die URL des eigenen Repositorys eintragen.
options(HTTPUserAgent = "bundestag-transcripts-downloader (R script for academic text analysis)",
        timeout = 120)

# ---- Links sammeln ----------------------------------------------------------

links_sammeln <- function(listen_id) {
  links <- character()
  offset <- 0
  repeat {
    verbindung <- url(sprintf(LISTEN_URL, listen_id, listen_id, offset), encoding = "UTF-8")
    html <- paste(readLines(verbindung, warn = FALSE), collapse = "\n")
    close(verbindung)

    neu <- setdiff(unique(regmatches(html, gregexpr(LINK_MUSTER, html))[[1]]), links)
    if (length(neu) == 0) break

    links <- c(links, neu)
    offset <- offset + 10
    Sys.sleep(LISTEN_PAUSE)
  }
  links
}

alle_links <- character()
for (wp in names(WAHLPERIODEN)) {
  message("Sammle Links der ", wp, ". Wahlperiode ...")
  links <- links_sammeln(WAHLPERIODEN[[wp]])
  message("  ", length(links), " Protokolle gefunden")
  alle_links <- c(alle_links, links)
}
alle_links <- alle_links[order(basename(alle_links))]

if (NUR_LINKS) {
  print(alle_links)
} else {

  # ---- Herunterladen --------------------------------------------------------

  # recursive = TRUE, damit auch mehrstufige Pfade angelegt werden
  # (z. B. ZIELORDNER <- "daten/Plenarprotokolle")
  dir.create(ZIELORDNER, showWarnings = FALSE, recursive = TRUE)
  if (!dir.exists(ZIELORDNER)) {
    stop("Zielordner konnte nicht angelegt werden: ", ZIELORDNER,
         "\nArbeitsverzeichnis ist: ", getwd(),
         "\nStimmt das Arbeitsverzeichnis (setwd)?")
  }

  zu_laden <- alle_links[!file.exists(file.path(ZIELORDNER, basename(alle_links)))]

  message("\n", length(alle_links), " insgesamt, ",
          length(alle_links) - length(zu_laden), " bereits vorhanden, ",
          length(zu_laden), " zu laden")
  message("Zielordner: ", normalizePath(ZIELORDNER), "\n")

  fehlgeschlagen <- character()
  for (i in seq_along(zu_laden)) {
    link <- zu_laden[i]
    datei <- file.path(ZIELORDNER, basename(link))
    temp <- paste0(datei, ".part")

    ok <- tryCatch({
      download.file(link, temp, mode = "wb", quiet = TRUE)
      file.rename(temp, datei)
    }, error = function(e) {
      message(sprintf("[%d/%d] FEHLER bei %s: %s", i, length(zu_laden), basename(link), conditionMessage(e)))
      FALSE
    })

    if (isTRUE(ok)) {
      message(sprintf("[%d/%d] %s (%d KB)", i, length(zu_laden), basename(link), file.size(datei) %/% 1024))
    } else {
      unlink(temp)
      fehlgeschlagen <- c(fehlgeschlagen, basename(link))
    }

    if (i < length(zu_laden)) Sys.sleep(DOWNLOAD_PAUSE)
  }

  message("\nFertig. ", length(zu_laden) - length(fehlgeschlagen), " geladen, ",
          length(fehlgeschlagen), " fehlgeschlagen.")
  if (length(fehlgeschlagen) > 0) {
    message("Fehlgeschlagen: ", paste(fehlgeschlagen, collapse = ", "),
            " (Skript einfach erneut starten)")
  }
}
