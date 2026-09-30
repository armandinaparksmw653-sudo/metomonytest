-- | Two real, single-signal location-for-artifact examples (WiMCor
-- LOCATION-for-ARTIFACT medium, live-Wikidata-verified): "Gloucester has
-- a Norman nave..." and "the lady chapel of Ely...", simplified to the
-- same representative-tree style already used for Waterloo/Molde.
--
-- Unlike Molde, a live SPARQL check found NO real ambiguity here:
-- exactly one entity at each place has Wikidata type Q56242250
-- ("Anglican or Episcopal cathedral") -- the cathedral itself -- so a
-- single Requires (HasSort Artifact) signal already narrows to a unique
-- candidate, the same "one real signal, already unique" shape as
-- Cupertino/Apple.
module Metonymy.Cathedrals
  ( gloucesterContext
  , elyContext
  , gloucesterSource
  , gloucesterCathedral
  , elySource
  , elyCathedral
  ) where

import Metonymy.Contextual
import Metonymy.Types

anchor :: String -> String -> String -> Int -> Int -> LexicalAnchor
anchor constructor lemma surface start end =
  LexicalAnchor constructor lemma surface start end

cathedralContext :: Snapshot -> EntityId -> String -> Int -> String -> String -> Context
cathedralContext snapshot source placeName placeEnd noun context =
  Context
    { contextTree =
        LexicalApply
          "Pred"
          [ LexicalLeaf (anchor "OpenPN" (lower placeName) placeName 0 placeEnd) []
          , LexicalApply
              "Compl"
              [ LexicalLeaf (anchor "Verb" "have" "has" (placeEnd + 1) (placeEnd + 4)) []
              , LexicalLeaf
                  (anchor "Noun" noun noun (placeEnd + 7) (placeEnd + 7 + length noun))
                  [Requires (HasSort Artifact)]
              ]
          ]
    , contextSnapshotHash = snapshotHash snapshot
    , contextSource = source
    , contextAction = "have"
    , contextRole = SubjectHole
    , contextConstraints =
        [ ContextConstraint
            (anchor "Noun" noun noun (placeEnd + 7) (placeEnd + 7 + length noun))
            (Requires (HasSort Artifact))
            context
        ]
    , contextRuleProvenance = [context]
    }
  where
    lower = map toLowerChar
    toLowerChar character
      | character >= 'A' && character <= 'Z' =
          toEnum (fromEnum character + 32)
      | otherwise = character

gloucesterContext, elyContext :: Snapshot -> Context
gloucesterContext snapshot =
  cathedralContext
    snapshot
    gloucesterSource
    "Gloucester"
    10
    "nave"
    "wimcor:real:gloucester-cathedral-nave"
elyContext snapshot =
  cathedralContext
    snapshot
    elySource
    "Ely"
    3
    "chapel"
    "wimcor:real:ely-cathedral-chapel"

gloucesterSource, gloucesterCathedral, elySource, elyCathedral :: EntityId
gloucesterSource = EntityId "Q170497"
gloucesterCathedral = EntityId "Q262500"
elySource = EntityId "Q209176"
elyCathedral = EntityId "Q579004"
