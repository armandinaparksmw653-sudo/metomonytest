GHC ?= ghc
GF ?= gf
AGDA ?= agda
AGDA_RTS ?= +RTS -M8G -RTS
CUBICAL_LIB ?= $(HOME)/.cache/metonymy/cubical-v0.5
RGL_LIB ?= $(HOME)/.cache/metonymy/gf-rgl-lib
RGL_PATH = $(RGL_LIB)/alltenses:$(RGL_LIB)/prelude

.PHONY: all grammar formal formal-artifact checker engine test evaluation-test \
	generated-check verbnet-generated-check verify \
	framenet-generated-check qid-fiber-test report reproduce clean

all: grammar formal checker engine

grammar:
	./auxiliary/scripts/generate_gf_lexicon.py
	$(GF) -path="$(RGL_PATH)" -make auxiliary/grammar/GeneratedMetonymyEng.gf

formal:
	$(AGDA) $(AGDA_RTS) --safe -i "$(CUBICAL_LIB)" -i formal-verification \
		formal-verification/Metonymy/Soundness.agda
	$(AGDA) $(AGDA_RTS) --safe -i "$(CUBICAL_LIB)" -i formal-verification \
		formal-verification/Metonymy/PublicationTheorems.agda
	$(AGDA) $(AGDA_RTS) --safe -i "$(CUBICAL_LIB)" -i formal-verification \
		formal-verification/Metonymy/Contextual.agda
	$(AGDA) $(AGDA_RTS) --safe -i "$(CUBICAL_LIB)" -i formal-verification \
		formal-verification/Metonymy/ContextualTower.agda
	$(AGDA) $(AGDA_RTS) --safe -i "$(CUBICAL_LIB)" -i formal-verification \
		formal-verification/Metonymy/ContextualModel.agda
	$(AGDA) $(AGDA_RTS) --safe -i "$(CUBICAL_LIB)" -i formal-verification \
		formal-verification/Metonymy/FilteredContext.agda
	$(AGDA) $(AGDA_RTS) --safe -i "$(CUBICAL_LIB)" -i formal-verification \
		formal-verification/Metonymy/CompilerSoundness.agda
	$(AGDA) $(AGDA_RTS) --safe -i "$(CUBICAL_LIB)" -i formal-verification \
		formal-verification/Metonymy/FilteredRuntime.agda
	$(AGDA) $(AGDA_RTS) --safe -i "$(CUBICAL_LIB)" -i formal-verification \
		formal-verification/Metonymy/TwoTruncatedContext.agda
	$(AGDA) $(AGDA_RTS) --safe -i "$(CUBICAL_LIB)" -i formal-verification \
		formal-verification/Metonymy/TwoTruncatedRuntime.agda

formal-artifact: formal
	command -v rg >/dev/null || \
		{ echo "formal-artifact requires ripgrep (rg) to check for postulates" >&2; exit 1; }
	! rg -n \
		'(^|[[:space:]])(postulate|TERMINATING|NON_TERMINATING|NO_POSITIVITY)([[:space:]]|$$)' \
		formal-verification/Metonymy --glob '*.agda'
	python3 formal-verification/Metonymy/generate_manifest.py --check

checker:
	mkdir -p build/agda
	$(AGDA) $(AGDA_RTS) --safe --compile --no-main --compile-dir=build/agda \
		--ghc-flag=-Wno-star-is-type \
		-i formal-verification formal-verification/Metonymy/Checker.agda
	python3 auxiliary/scripts/generate_malonzo_api.py \
		--source build/agda/MAlonzo/Code/Metonymy/Checker.hs \
		--output build/agda/Metonymy/CheckerAPI.hs

engine: checker
	mkdir -p build/engine build/test
	$(GHC) --make -XGHC2021 -XDerivingStrategies -O1 -Wall -Wcompat -Widentities \
		-itower/engine/src -ibuild/agda \
		-outputdir build/engine \
		tower/engine/app/Main.hs \
		-o build/metonymy
	$(GHC) --make -XGHC2021 -XDerivingStrategies -O1 -Wall -Wcompat -Widentities \
		-itower/engine/src -ibuild/agda \
		-outputdir build/engine \
		tower/engine/app/Report.hs \
		-o build/metonymy-report
	$(GHC) --make -XGHC2021 -XDerivingStrategies -O1 -Wall -Wcompat -Widentities \
		-itower/engine/src -ibuild/agda \
		-outputdir build/test \
		tower/engine/test/Main.hs \
		-o build/metonymy-tests

test: all
	./build/metonymy-tests

report: all
	mkdir -p build/evaluation
	./build/metonymy-report --output build/evaluation/tower-report.txt

evaluation-test:
	python3 -m unittest discover -s auxiliary/tests/evaluation -p 'test_*.py'

generated-check:
	./auxiliary/scripts/generate_gf_lexicon.py
	git diff --exit-code -- \
		auxiliary/grammar/GeneratedMetonymy.gf \
		auxiliary/grammar/GeneratedMetonymyEng.gf \
		auxiliary/data/contextual-gf-actions.json \
		auxiliary/data/contextual-gf-nouns.json

framenet-generated-check:
	python3 auxiliary/scripts/generate_framenet_capabilities.py
	git diff --exit-code -- auxiliary/data/framenet-role-capabilities.json

verbnet-generated-check:
	./auxiliary/scripts/import_verbnet.py
	git diff --exit-code -- \
		auxiliary/data/verbnet-predicates.tsv \
		auxiliary/data/verbnet-actions.tsv \
		auxiliary/data/verbnet-action-roles.tsv

verify:
	$(MAKE) test
	$(MAKE) evaluation-test
	$(MAKE) generated-check
	$(MAKE) framenet-generated-check
	$(MAKE) qid-fiber-test
	$(MAKE) report

qid-fiber-test: engine
	python3 auxiliary/scripts/extract_wikidata_snapshot.py verify \
		--snapshot tower/data/wikidata-qid-snapshot
	python3 auxiliary/scripts/evaluation/extract_qid_fibers.py \
		--dataset auxiliary/evaluation/qid-fiber/waterloo-dataset.jsonl \
		--engine build/metonymy \
		--output build/evaluation/waterloo-contextual-inference.jsonl
	python3 auxiliary/scripts/evaluation/score_qid_fibers.py \
		--inference build/evaluation/waterloo-contextual-inference.jsonl \
		--gold auxiliary/evaluation/qid-fiber/waterloo-gold.jsonl \
		--output build/evaluation/waterloo-contextual-report.json

reproduce:
	./scripts/reproduce.sh

clean:
	rm -rf build dist-newstyle
	rm -f auxiliary/grammar/*.gfo Metonymy.pgf GeneratedMetonymy.pgf
	rm -f formal-verification/Metonymy/*.agdai
