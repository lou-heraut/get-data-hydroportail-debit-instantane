.PHONY: help etat suivi avancement journal tourne \
        inventaire telecharger stopper resume cas \
        tests controler

# Le cas sur lequel tout porte. Surchargeable : make avancement CAS=2026-09_jeu-de-test
CAS     ?= 2026-09_eclusees-rmc
RACINE  ?= donnees_hydroportail
PY      := .python_env/bin/python
JOURNAL ?= ../.telechargement_$(CAS).log

GREEN  := \033[0;32m
YELLOW := \033[0;33m
NC     := \033[0m

help: ## Affiche cette aide
	@echo "$(GREEN)Débits instantanés HydroPortail, cas $(CAS)$(NC)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-14s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "  Variables : CAS, RACINE, JOURNAL"

# ─── VOIR CE QUI SE PASSE ────────────────────────────────────────────────────

etat: ## Résumé en dix lignes : téléchargement, avancement, poids, dépôt
	@$(MAKE) --no-print-directory tourne
	@$(MAKE) --no-print-directory avancement
	@echo ""
	@echo "$(GREEN)Dépôt$(NC)"
	@git status -sb | head -3

tourne: ## Dit si un téléchargement est en cours pour ce cas
	@if pgrep -f "python download_hydroportail\.py --cas $(CAS)$$" > /dev/null; then \
		echo "$(GREEN)Téléchargement en cours$(NC) (pid $$(pgrep -f "python download_hydroportail\.py --cas $(CAS)$$" | head -1))"; \
	else \
		echo "$(YELLOW)Aucun téléchargement en cours$(NC)"; \
	fi

avancement: ## Où en est le téléchargement, et ce qui est déjà sur disque
	@echo ""
	@echo "$(GREEN)Avancement$(NC)"
	@if [ -f $(JOURNAL) ]; then \
		sed -n '/Téléchargement de/,$$p' $(JOURNAL) | grep -E '^  \[' | tail -1; \
		sed -n '/Téléchargement de/,$$p' $(JOURNAL) | grep -E 'reste environ' | tail -1; \
	else \
		echo "  pas de journal : $(JOURNAL)"; \
	fi
	@echo "  fichiers écrits : $$(ls $(RACINE)/$(CAS)/mesures/*.parquet 2>/dev/null | wc -l)"
	@echo "  poids sur disque : $$(du -sh $(RACINE)/$(CAS) 2>/dev/null | cut -f1)"
	@echo "  cache partagé : $$(du -sh $(RACINE)/.sources 2>/dev/null | cut -f1)"

suivi: ## Suit le journal en direct (Ctrl-C pour sortir, le téléchargement continue)
	@tail -f $(JOURNAL)

journal: ## Les trente dernières lignes du journal
	@tail -30 $(JOURNAL)

# ─── AGIR SUR LE CAS ─────────────────────────────────────────────────────────

inventaire: ## Ce que le cas contient, sans télécharger de chronique
	$(PY) download_hydroportail.py --cas $(CAS) --racine $(RACINE) --inventaire

telecharger: ## Lance le téléchargement, détaché de ce terminal
	@if pgrep -f "python download_hydroportail\.py --cas $(CAS)$$" > /dev/null; then \
		echo "Déjà en cours, rien à faire."; exit 1; \
	fi
	@echo "" >> $(JOURNAL)
	@echo "=== lancé le $$(date '+%Y-%m-%d %H:%M') ===" >> $(JOURNAL)
	@setsid nohup $(PY) download_hydroportail.py --cas $(CAS) --racine $(RACINE) \
		>> $(JOURNAL) 2>&1 < /dev/null & \
	sleep 2; echo "Lancé. Journal : $(JOURNAL), suivi : make suivi"

stopper: ## Arrête le téléchargement ; le cache garde ce qui est déjà reçu
	@pkill -f "python download_hydroportail\.py --cas $(CAS)$$" \
		&& echo "Arrêté. Relancer ne recoûtera rien de ce qui est en cache." \
		|| echo "Rien à arrêter."

resume: ## Le résumé des tables du cas, sans rien télécharger
	@$(PY) -c "import logging; logging.basicConfig(level=logging.INFO, format='%(message)s'); \
		from hydroportail import summary; summary('$(RACINE)/$(CAS)')"

cas: ## Liste les cas, ce qui est demandé et ce qui est obtenu
	@echo "$(GREEN)Demandes$(NC)"
	@for d in ressources/*/; do \
		n=$$(grep -c . "$$d/stations.txt" 2>/dev/null || echo 0); \
		printf "  %-24s %3s stations demandées\n" "$$(basename $$d)" "$$n"; \
	done
	@echo "$(GREEN)Jeux produits$(NC)"
	@for d in $(RACINE)/*/; do \
		[ "$$(basename $$d)" = ".sources" ] && continue; \
		p=$$(ls "$$d"/mesures/*.parquet 2>/dev/null | wc -l); \
		printf "  %-24s %3s fichiers, %s\n" "$$(basename $$d)" "$$p" "$$(du -sh $$d | cut -f1)"; \
	done

# ─── CONTRÔLER ───────────────────────────────────────────────────────────────

tests: ## Les tests unitaires, instantanés
	$(PY) -m pytest -q

controler: ## Les cinq contrôles sur le jeu produit, puis le datapackage
	$(PY) verifier_hydroportail.py --cas $(CAS) --racine $(RACINE)
	@$(PY) -c "from frictionless import Package; \
		print('datapackage valide :', \
		Package('$(RACINE)/$(CAS)/datapackage.json').validate().valid)"
