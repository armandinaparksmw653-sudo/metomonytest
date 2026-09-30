-- | Five fully fictional (Q)metonymy "towers", each a place-like source
-- entity with four candidate institutional readings sharing two Sorts
-- pairwise, backed by data/synthetic-towers-snapshot -- NOT real Wikidata
-- data (see that directory's manifest.json for the explicit disclosure).
--
-- Built to answer a direct question this session's Python-level synthetic
-- context-trigger dictionary round (data/contextual-context-triggers.json)
-- never answered on its own: does the REAL compiled engine + Agda checker
-- (Metonymy.Contextual/Metonymy.ContextualChecked, not just
-- scripts/contextual_rule_compiler.py in isolation) actually narrow a
-- fiber to a unique target when two independent Sort-based signals are
-- stacked? See engine/test/Main.hs's SyntheticTowers assertions.
--
-- Every one of the 78 new dictionary entries added this session is
-- strength: "prefers" (honest -- none individually verified against a
-- real corpus/Wikidata). Metonymy.Contextual.applyConstraints only lets
-- 'Requires'-kind constraints actually eliminate candidates
-- ('Prefers'-kind constraints rank but never filter, by design -- see
-- Contextual.hs's own applyConstraints). So each tower here is built
-- BOTH ways, on purpose, not as a shortcut: 'towerContextPreferring'
-- mirrors what is actually in the shipped dictionary today (both
-- constraints Prefers) and is expected to NOT narrow the fiber;
-- 'towerContextRequiring' is an explicitly hypothetical "what if these
-- were individually verified and promoted to requires" variant, and is
-- expected to narrow to exactly one candidate. Neither result is
-- fabricated to match an assumption -- both are asserted and read from
-- the real compiled Agda checker via CI.
module Metonymy.SyntheticTowers
  ( TowerFixture (..)
  , towers
  , towerContextPreferring
  , towerContextRequiring
  , towerContextSingle
  ) where

import Metonymy.Contextual
import Metonymy.Types

data TowerFixture = TowerFixture
  { towerLabel :: String
  , towerSource :: EntityId
  , towerFirstSort :: Sort
  , towerSecondSort :: Sort
  , towerBothCandidate :: EntityId
  , towerFirstOnlyCandidate :: EntityId
  , towerSecondOnlyCandidate :: EntityId
  , towerDecoyCandidate :: EntityId
  }
  deriving stock (Eq, Show)

-- | data/synthetic-towers-snapshot's five fictional clusters, one per
-- tower. Each candidate's actual Sort membership is asserted directly
-- against the snapshot's own claims.jsonl in engine/test/Main.hs, not
-- assumed here -- this table only names which EntityId is which role.
towers :: [TowerFixture]
towers =
  [ TowerFixture
      "ashford-university-research"
      (EntityId "ASHFORD")
      University
      ResearchInstitution
      (EntityId "ASHFORD_UNIVERSITY")
      (EntityId "ASHFORD_COLLEGE")
      (EntityId "ASHFORD_LAB")
      (EntityId "ASHFORD_MUSEUM")
  , TowerFixture
      "boutiqueville-clothing-brand"
      (EntityId "BOUTIQUEVILLE")
      Clothing
      Brand
      (EntityId "BOUTIQUEVILLE_FASHION_HOUSE")
      (EntityId "BOUTIQUEVILLE_TAILOR_SHOP")
      (EntityId "BOUTIQUEVILLE_LOGO_STUDIO")
      (EntityId "BOUTIQUEVILLE_BAKERY")
  , TowerFixture
      "millbrook-business-research"
      (EntityId "MILLBROOK")
      BusinessOrganization
      ResearchInstitution
      (EntityId "MILLBROOK_R_AND_D_FIRM")
      (EntityId "MILLBROOK_CORP")
      (EntityId "MILLBROOK_INSTITUTE")
      (EntityId "MILLBROOK_PARK")
  , TowerFixture
      "vinedale-drink-food"
      (EntityId "VINEDALE")
      Drinkable
      Food
      (EntityId "VINEDALE_ESTATE")
      (EntityId "VINEDALE_WINERY")
      (EntityId "VINEDALE_ORCHARD")
      (EntityId "VINEDALE_QUARRY")
  , TowerFixture
      "relaypoint-communication-programme"
      (EntityId "RELAYPOINT")
      CommunicationContent
      Programme
      (EntityId "RELAYPOINT_NETWORK")
      (EntityId "RELAYPOINT_STATION")
      (EntityId "RELAYPOINT_SHOWCASE")
      (EntityId "RELAYPOINT_DEPOT")
  ]

-- | Both of the tower's two Sort constraints, as Prefers -- exactly what
-- data/contextual-context-triggers.json's synthetic entries actually are
-- today. Expect the fiber to stay at all four candidates (Prefers never
-- filters); expect stagePreferredCandidates to correctly single out
-- towerBothCandidate as matching both preferences.
towerContextPreferring :: Snapshot -> TowerFixture -> Context
towerContextPreferring snapshot fixture =
  towerContextWith "prefers-both" snapshot fixture Prefers
    [towerFirstSort fixture, towerSecondSort fixture]

-- | Both of the tower's two Sort constraints, as Requires -- an explicitly
-- hypothetical "if these were individually verified and promoted"
-- variant, not the dictionary's actual current strength. Expect this to
-- narrow the fiber to exactly towerBothCandidate.
towerContextRequiring :: Snapshot -> TowerFixture -> Context
towerContextRequiring snapshot fixture =
  towerContextWith "requires-both" snapshot fixture Requires
    [towerFirstSort fixture, towerSecondSort fixture]

-- | Exactly one of the tower's two Sort constraints, as Requires -- used
-- to confirm each signal ALONE is genuinely ambiguous (two survivors),
-- so the "requires both" narrowing is a real conjunction, not a case
-- where one signal alone already sufficed.
towerContextSingle :: Snapshot -> TowerFixture -> Sort -> Context
towerContextSingle snapshot fixture sortChosen =
  towerContextWith "requires-single" snapshot fixture Requires [sortChosen]

towerContextWith ::
  String ->
  Snapshot ->
  TowerFixture ->
  (Requirement -> ConstraintPayload) ->
  [Sort] ->
  Context
towerContextWith variant snapshot fixture makePayload sorts =
  Context
    { contextTree =
        LexicalApply
          "Pred"
          [ LexicalLeaf (anchor "OpenPN" sourceLemma sourceLemma 0 (length sourceLemma)) []
          , LexicalApply
              "Compl"
              (LexicalLeaf (anchor "Verb" "announce" "announces" 0 8) [] : leaves)
          ]
    , contextSnapshotHash = snapshotHash snapshot
    , contextSource = towerSource fixture
    , contextAction = "announce"
    , contextRole = ObjectHole
    , contextConstraints = constraints
    , contextRuleProvenance = map constraintProvenance constraints
    }
  where
    sourceLemma = towerLabel fixture
    leaves = [LexicalLeaf (anchor "Noun" lemma lemma start (start + length lemma)) [] | (lemma, start) <- zip lemmas starts]
    lemmas = map show sorts
    starts = scanl (\offset lemma -> offset + length lemma + 1) 9 lemmas
    constraints =
      [ ContextConstraint
          (anchor "Noun" lemma lemma start (start + length lemma))
          (makePayload (HasSort sortChosen))
          (provenanceFor lemma)
      | (sortChosen, lemma, start) <- zip3 sorts lemmas starts
      ]
    provenanceFor lemma =
      "test:synthetic-tower:" <> towerLabel fixture <> ":" <> variant <> ":" <> lemma

anchor :: String -> String -> String -> Int -> Int -> LexicalAnchor
anchor = LexicalAnchor
