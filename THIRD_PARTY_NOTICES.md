# Third-party notices

This repository does not vendor the build dependencies below. Exact source
commits and artifact hashes are recorded in `toolchain.lock.json`.

## Agda Cubical

- Source: <https://github.com/agda/cubical>
- Pinned commit: `132a2a3197b490c571356f0399a2a6fbfab40f2a`
- License: MIT
- Copyright: Agda Cubical contributors

The complete license is available in the pinned source repository.

## Grammatical Framework

- GF compiler: <https://github.com/GrammaticalFramework/gf-core>
- Version: 3.12.0
- Compiler license: GPL; runtime components have their upstream licenses.
- GF Resource Grammar Library:
  <https://github.com/GrammaticalFramework/gf-rgl>
- Pinned RGL commit: `e825d9223305ad3066e1ac5b276bcdedd2fcd15a`
- RGL license: LGPL-3.0 and BSD; application grammars derived through the
  grammar API may choose their application license under the upstream
  notice.

The complete GF and RGL license texts are distributed by their respective
pinned source repositories.

## VerbNet 3.4

- Source: <https://github.com/cu-clear/verbnet>
- Pinned commit: `ae8e9cfdc2c0d3414b748763612f1a0a34194cc1`
- Upstream terms:
  <https://verbs.colorado.edu/verbnet_downloads/downloads.html>

`data/verbnet-predicates.tsv` is a derived selectional-preference snapshot.
VerbNet permits use, copying, modification, and distribution provided the
upstream copyright notice, terms, and disclaimer are preserved. Users
redistributing the snapshot must retain this notice and consult the pinned
upstream terms.

## Wikidata

- Source: <https://www.wikidata.org/>
- License: CC0 1.0

`data/wikidata-author-works.tsv` is an offline structured-data snapshot.

## SemEval-2007 Task 8

The repository does not redistribute SemEval contexts. The benchmark is
derived from the British National Corpus and remains subject to applicable
BNC/task distribution terms. Only a text-free aggregate, instance counts,
and source-file hash are committed.

## WiMCor v1.1

- Source: <https://kevinalexmathews.github.io/software/>
- Archive SHA-256:
  `df4d52a63d9c03cdce543f5d9638efafab73736ce117f90352373fd7051f8e2b`
- Dataset license: CC BY-SA 3.0
- Extraction code: GPL-3.0

The corpus is not committed. Only adapters, hashes, and aggregate metrics
are distributed here.

## ConMeC

- Source: <https://github.com/SaptGhosh/ConMeC>
- Pinned revision: `ec6914770b86eb82347724e22c7b627598644ba4`
- CSV SHA-256:
  `cd692d6953bb719bb6aeb0ac13df7c3641564918c38cf39ad15bcf20c8b76d90`
- Repository metadata license: Apache-2.0

ConMeC contains Wikipedia-derived text. Users must additionally preserve
applicable Wikipedia attribution and ShareAlike obligations. The corpus is
not committed by this project.
