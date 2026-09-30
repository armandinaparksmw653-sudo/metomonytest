-- | A real, single-signal location-for-event example (WiMCor LOCATION-
-- for-EVENT medium, the WiMCor category with by far the fewest real
-- subject-position candidates found this session -- 422 metonymic rows,
-- most not subject-position at all): "2015 Busan marked the release of
-- the drama Zubaan", simplified to "Busan marks a release".
--
-- Live-Wikidata-verified: exactly one entity at Busan has type Q220505
-- ("film festival") -- the Busan International Film Festival itself --
-- so a single Requires (HasSort Event) signal already narrows to a
-- unique candidate, the same one-signal shape as Cupertino/Apple and
-- Gloucester/Ely, in a domain (festivals/events) this project's real
-- examples did not reach until now.
module Metonymy.Busan
  ( busanContext
  , busanSource
  , busanFilmFestival
  ) where

import Metonymy.Contextual
import Metonymy.Types

anchor :: String -> String -> String -> Int -> Int -> LexicalAnchor
anchor constructor lemma surface start end =
  LexicalAnchor constructor lemma surface start end

busanContext :: Snapshot -> Context
busanContext snapshot =
  Context
    { contextTree =
        LexicalApply
          "Pred"
          [ LexicalLeaf (anchor "OpenPN" "busan" "Busan" 0 5) []
          , LexicalApply
              "Compl"
              [ LexicalLeaf (anchor "Verb" "mark" "marks" 6 11) []
              , LexicalLeaf
                  (anchor "Noun" "release" "release" 14 21)
                  [Requires (HasSort Event)]
              ]
          ]
    , contextSnapshotHash = snapshotHash snapshot
    , contextSource = busanSource
    , contextAction = "mark"
    , contextRole = SubjectHole
    , contextConstraints =
        [ ContextConstraint
            (anchor "Noun" "release" "release" 14 21)
            (Requires (HasSort Event))
            "wimcor:real:busan-film-festival-release"
        ]
    , contextRuleProvenance = ["wimcor:real:busan-film-festival-release"]
    }

busanSource, busanFilmFestival :: EntityId
busanSource = EntityId "Q16520"
busanFilmFestival = EntityId "Q482633"
