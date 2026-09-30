-- | The first real, live-Wikidata-verified Author-for-work example: "A
-- good deal of modern poetry was banned at the time, so he studied the
-- Romantic poet Novalis, whose Hymns to the Night left a great
-- impression on him" (real ConMeC METONYMIC/PRODUCER-category sentence,
-- target word "poet"), simplified to "he studied Novalis".
--
-- Architecturally this is the same transfer mechanism already used for
-- Container-for-content/Producer-for-product (Metonymy.ContainerContent),
-- not a new one: a single bridge relation (here Authored, inverse P50)
-- walked one hop from the source, filtered by a Requires signal on the
-- governing verb. The difference from the ContainerContent examples is
-- that this one is grounded in real Wikidata entities, not a hand-built
-- local graph -- the first real instance of the Sort vocabulary
-- (LiteraryWork, already registered for Q7725634 in
-- data/wikidata-qid-snapshot/rules.json) that had been defined since
-- early in the session but never actually exercised by a built example.
--
-- Live Wikidata check (wbgetentities on Q60684/Q128670/Q58178849):
-- Novalis (Q60684, human) has exactly two real P800 notable works, both
-- confirmed via their own P50 (author) claim: "Hymns to the Night"
-- (Q128670) and the novel "Heinrich von Ofterdingen" (Q58178849), both
-- typed P31 -> Q7725634 (literary work). Requires (HasSort LiteraryWork)
-- on the governing verb "study" correctly excludes Novalis himself (a
-- Human, not reachable via Authored from himself anyway) but does not
-- distinguish between his two works -- the real sentence's own further
-- disambiguation ("whose Hymns to the Night...") is same-sentence
-- coreference to a literally named work, not a type/relation signal
-- contextualFiber can consume -- so, honestly, this stays a two-
-- candidate result, the same shape as Waterloo/Rijeka/Eswatini.
module Metonymy.AuthorWork
  ( novalisContext
  , novalisSource
  , hymnsToTheNight
  , heinrichVonOfterdingen
  ) where

import Metonymy.Contextual
import Metonymy.Types

anchor :: String -> String -> String -> Int -> Int -> LexicalAnchor
anchor constructor lemma surface start end =
  LexicalAnchor constructor lemma surface start end

novalisContext :: Snapshot -> Context
novalisContext snapshot =
  Context
    { contextTree =
        LexicalApply
          "Pred"
          [ LexicalLeaf (anchor "HePN" "he" "he" 0 2) []
          , LexicalApply
              "Compl"
              [ LexicalLeaf
                  (anchor "Verb" "study" "studied" 3 10)
                  [Requires (HasSort LiteraryWork)]
              , LexicalLeaf (anchor "OpenPN" "novalis" "Novalis" 11 18) []
              ]
          ]
    , contextSnapshotHash = snapshotHash snapshot
    , contextSource = novalisSource
    , contextAction = "study"
    , contextRole = ObjectHole
    , contextConstraints =
        [ ContextConstraint
            (anchor "Verb" "study" "studied" 3 10)
            (Requires (HasSort LiteraryWork))
            "conmec:real:novalis-studied-poet"
        ]
    , contextRuleProvenance = ["conmec:real:novalis-studied-poet"]
    }

novalisSource, hymnsToTheNight, heinrichVonOfterdingen :: EntityId
novalisSource = EntityId "Q60684"
hymnsToTheNight = EntityId "Q128670"
heinrichVonOfterdingen = EntityId "Q58178849"
