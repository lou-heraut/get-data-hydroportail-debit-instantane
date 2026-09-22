.PHONY: help status running progress watch log \
        inventory download stop summary cases \
        tests check

# Le cas sur lequel tout porte. Surchargeable : make status CASE=2026-09_jeu-de-test
CASE ?= 2026-09_eclusees-rmc
ROOT ?= donnees_hydroportail
PY   := .python_env/bin/python
LOG  ?= ../.telechargement_$(CASE).log

GREEN  := \033[0;32m
YELLOW := \033[0;33m
NC     := \033[0m

help: ## Affiche cette aide
	@echo "$(GREEN)Débits instantanés HydroPortail, cas $(CASE)$(NC)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-12s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "  Variables : CASE, ROOT, LOG"

# ─── VOIR CE QUI SE PASSE ────────────────────────────────────────────────────

status: ## Résumé en dix lignes : téléchargement, avancement, poids, dépôt
	@$(MAKE) --no-print-directory running
	@$(MAKE) --no-print-directory progress
	@echo ""
	@echo "$(GREEN)Dépôt$(NC)"
	@git status -sb | head -3

running: ## Dit si un téléchargement est en cours pour ce cas
	@if pgrep -f "python download_hydroportail\.py --cas $(CASE)$$" > /dev/null; then \
		echo "$(GREEN)Téléchargement en cours$(NC) (pid $$(pgrep -f "python download_hydroportail\.py --cas $(CASE)$$" | head -1))"; \
	else \
		echo "$(YELLOW)Aucun téléchargement en cours$(NC)"; \
	fi

progress: ## Où en est le téléchargement, et ce qui est déjà sur disque
	@echo ""
	@echo "$(GREEN)Avancement$(NC)"
	@if [ -f $(LOG) ]; then \
		sed -n '/Téléchargement de/,$$p' $(LOG) | grep -E '^  \[' | tail -1; \
		sed -n '/Téléchargement de/,$$p' $(LOG) | grep -E 'reste environ' | tail -1; \
	else \
		echo "  pas de journal : $(LOG)"; \
	fi
	@echo "  fichiers écrits : $$(ls $(ROOT)/$(CASE)/mesures/*.parquet 2>/dev/null | wc -l)"
	@echo "  poids sur disque : $$(du -sh $(ROOT)/$(CASE) 2>/dev/null | cut -f1)"
	@echo "  cache partagé : $$(du -sh $(ROOT)/.sources 2>/dev/null | cut -f1)"

watch: ## Suit le journal en direct (Ctrl-C pour sortir, le téléchargement continue)
	@tail -f $(LOG)

log: ## Les trente dernières lignes du journal
	@tail -30 $(LOG)

# ─── AGIR SUR LE CAS ─────────────────────────────────────────────────────────

inventory: ## Ce que le cas contient, sans télécharger de chronique
	$(PY) download_hydroportail.py --cas $(CASE) --racine $(ROOT) --inventaire

download: ## Lance le téléchargement, détaché de ce terminal
	@if pgrep -f "python download_hydroportail\.py --cas $(CASE)$$" > /dev/null; then \
		echo "Déjà en cours, rien à faire."; exit 1; \
	fi
	@echo "" >> $(LOG)
	@echo "=== lancé le $$(date '+%Y-%m-%d %H:%M') ===" >> $(LOG)
	@setsid nohup $(PY) download_hydroportail.py --cas $(CASE) --racine $(ROOT) \
		>> $(LOG) 2>&1 < /dev/null & \
	sleep 2; echo "Lancé. Journal : $(LOG), suivi : make watch"

stop: ## Arrête le téléchargement ; le cache garde ce qui est déjà reçu
	@pkill -f "python download_hydroportail\.py --cas $(CASE)$$" \
		&& echo "Arrêté. Relancer ne recoûtera rien de ce qui est en cache." \
		|| echo "Rien à arrêter."

summary: ## Le résumé des tables du cas, sans rien télécharger
	@$(PY) -c "import logging; logging.basicConfig(level=logging.INFO, format='%(message)s'); \
		from hydroportail import summary; summary('$(ROOT)/$(CASE)')"

cases: ## Liste les cas, ce qui est demandé et ce qui est obtenu
	@echo "$(GREEN)Demandes$(NC)"
	@for d in ressources/*/; do \
		n=$$(grep -c . "$$d/stations.txt" 2>/dev/null || echo 0); \
		printf "  %-24s %3s stations demandées\n" "$$(basename $$d)" "$$n"; \
	done
	@echo "$(GREEN)Jeux produits$(NC)"
	@for d in $(ROOT)/*/; do \
		[ "$$(basename $$d)" = ".sources" ] && continue; \
		p=$$(ls "$$d"/mesures/*.parquet 2>/dev/null | wc -l); \
		printf "  %-24s %3s fichiers, %s\n" "$$(basename $$d)" "$$p" "$$(du -sh $$d | cut -f1)"; \
	done

# ─── CONTRÔLER ───────────────────────────────────────────────────────────────

tests: ## Les tests unitaires, instantanés
	$(PY) -m pytest -q

check: ## Les cinq contrôles sur le jeu produit, puis le datapackage
	$(PY) verifier_hydroportail.py --cas $(CASE) --racine $(ROOT)
	@$(PY) -c "from frictionless import Package; \
		print('datapackage valide :', \
		Package('$(ROOT)/$(CASE)/datapackage.json').validate().valid)"
