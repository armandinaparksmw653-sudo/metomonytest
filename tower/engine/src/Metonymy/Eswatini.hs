-- | A real, live-Wikidata-verified Container-turned-jurisdiction example:
-- "The cabinet of eSwatini was placed in quarantine after Transport
-- Minister Ndlaluhlaza Ndwandwe tested positive for COVID-19" (real
-- ConMeC CONTAINER-category sentence), simplified to "Eswatini has a
-- cabinet".
--
-- Corrects an earlier plan to model this as Container-for-HumanGroup: a
-- direct Wikidata check found "Cabinet of Eswatini" (Q97473385) has no
-- P131/P159/P17 link back to Eswatini at all, only P1001 ("applies to
-- jurisdiction") -- so this is architecturally the same location-for-
-- institution family as Waterloo/Molde/Gloucester, just walked via a new
-- relation (GovernedBy, inverse P1001) instead of InstitutionOf.
--
-- A live SPARQL check found 88 real entities with P1001 -> Eswatini
-- (laws, ministries, several cabinet formations). Requires (HasSort
-- Government) -- via the specific cabinet-formation class Q97473385,
-- not the country's government in general -- narrows that down to
-- exactly the two real cabinet formations on record: the Ambrose
-- Mandvulo Dlamini Cabinet (Q114513825, 2018-11-02 to 2023-11-13,
-- covering the real sentence's COVID-19-era timeframe) and the Russell
-- Dlamini Cabinet (Q123554307, from 2023-11-13, after that timeframe).
-- Unlike Molde, no further lexical signal in the sentence distinguishes
-- which specific cabinet formation is meant (the real distinguishing
-- fact -- which one was in office when this happened -- is a date, not
-- a word in the sentence), so this stays an honest two-candidate result,
-- the same shape as Waterloo.
module Metonymy.Eswatini
  ( eswatiniContext
  , eswatiniSource
  , ambroseMandvuloDlaminiCabinet
  , russellDlaminiCabinet
  ) where

import Metonymy.Contextual
import Metonymy.Types

anchor :: String -> String -> String -> Int -> Int -> LexicalAnchor
anchor constructor lemma surface start end =
  LexicalAnchor constructor lemma surface start end

eswatiniContext :: Snapshot -> Context
eswatiniContext snapshot =
  Context
    { contextTree =
        LexicalApply
          "Pred"
          [ LexicalLeaf (anchor "OpenPN" "eswatini" "Eswatini" 0 8) []
          , LexicalApply
              "Compl"
              [ LexicalLeaf (anchor "Verb" "have" "has" 9 12) []
              , LexicalLeaf
                  (anchor "Noun" "cabinet" "cabinet" 15 22)
                  [Requires (HasSort Government)]
              ]
          ]
    , contextSnapshotHash = snapshotHash snapshot
    , contextSource = eswatiniSource
    , contextAction = "have"
    , contextRole = SubjectHole
    , contextConstraints =
        [ ContextConstraint
            (anchor "Noun" "cabinet" "cabinet" 15 22)
            (Requires (HasSort Government))
            "conmec:real:eswatini-cabinet-quarantine"
        ]
    , contextRuleProvenance = ["conmec:real:eswatini-cabinet-quarantine"]
    }

eswatiniSource, ambroseMandvuloDlaminiCabinet, russellDlaminiCabinet :: EntityId
eswatiniSource = EntityId "Q1050"
ambroseMandvuloDlaminiCabinet = EntityId "Q114513825"
russellDlaminiCabinet = EntityId "Q123554307"
