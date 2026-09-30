module Metonymy.Contextual
  ( LexicalAnchor (..)
  , ConstraintPayload (..)
  , ContextConstraint (..)
  , LexicalTree (..)
  , Context (..)
  , Snapshot (..)
  , ConstraintProof (..)
  , SnapshotObstruction (..)
  , ContextualCandidate (..)
  , FiberStage (..)
  , payloadIsPreference
  , validateContext
  , contextualFiber
  , stageTargets
  ) where

import Data.List (nubBy)
import Metonymy.Ontology
import Metonymy.Resolution (expandFiber)
import Metonymy.Types

data LexicalAnchor = LexicalAnchor
  { anchorGFConstructor :: String
  , anchorLemma :: String
  , anchorSurface :: String
  , anchorStart :: Int
  , anchorEnd :: Int
  }
  deriving stock (Eq, Show)

data ConstraintPayload
  = Requires Requirement
  | RequiresRelation Relation EntityId
  | RequiresSome Relation Requirement
  | Prefers Requirement
  | PrefersRelation Relation EntityId
  | PrefersSome Relation Requirement
  deriving stock (Eq, Show)

data ContextConstraint = ContextConstraint
  { constraintOrigin :: LexicalAnchor
  , constraintPayload :: ConstraintPayload
  , constraintProvenance :: String
  }
  deriving stock (Eq, Show)

data LexicalTree
  = LexicalLeaf LexicalAnchor [ConstraintPayload]
  | LexicalApply String [LexicalTree]
  deriving stock (Eq, Show)

-- | contextTree and contextConstraints are two views of the same lexical
-- structure: the tree records the surface constituent shape (for
-- validateTree's construction allowlist), while the flat constraint list
-- is what contextualFiber actually applies stage by stage. They are kept
-- as separate fields rather than computing one from the other on every
-- access, but that means nothing in this module enforces they agree.
--
-- 'Metonymy.Elaborator.elaborateContext' is the only constructor that
-- guarantees consistency: it derives contextConstraints from the tree via
-- collectConstraints, so origin and payload always match by construction
-- (constraintProvenance is always the placeholder "lexical-tree" on that
-- path, since a bare LexicalTree carries no real per-constraint
-- provenance). Call sites that need real provenance strings per
-- constraint -- Metonymy.ContextSpec's TSV scenario parser,
-- Metonymy.Waterloo's hand-written fixture -- construct both fields
-- directly instead, and are responsible for keeping the tree's leaf
-- anchors/payloads in the same order as contextConstraints; nothing here
-- checks that automatically, so a change to one side without the other is
-- a real, silent way to desync them. engine/test/Main.hs's "Waterloo tree
-- elaborates with ordered lexical origins" test partially guards this for
-- the Waterloo fixture by comparing elaborateContext's derived
-- (origin, payload) sequence against the hand-written one.
data Context = Context
  { contextTree :: LexicalTree
  , contextSnapshotHash :: String
  , contextSource :: EntityId
  , contextAction :: String
  , contextRole :: HoleRole
  , contextConstraints :: [ContextConstraint]
  , contextRuleProvenance :: [String]
  }
  deriving stock (Eq, Show)

data Snapshot = Snapshot
  { snapshotHash :: String
  , snapshotKnowledgeBase :: KnowledgeBase
  }
  deriving stock (Eq, Show)

data SnapshotObstruction
  = MissingRequirement ContextConstraint EntityId
  | MissingRelation ContextConstraint EntityId Relation EntityId
  | MissingRelated ContextConstraint EntityId Relation Requirement
  deriving stock (Eq, Show)

data ConstraintProof
  = RequirementConstraintProof ContextConstraint [Proof]
  | RelationConstraintProof ContextConstraint Proof
  | RelatedConstraintProof ContextConstraint Proof [Proof]
  deriving stock (Eq, Show)

data ContextualCandidate = ContextualCandidate
  { contextualFineMeaning :: FineMeaning
  , contextualProofs :: [ConstraintProof]
  }
  deriving stock (Eq, Show)

data FiberStage = FiberStage
  { stageIndex :: Int
  , stageConstraint :: Maybe ContextConstraint
  , stageCandidates :: [ContextualCandidate]
  , stageObstructions :: [SnapshotObstruction]
  , stagePreferredCandidates :: [ContextualCandidate]
  , stagePreferenceMisses :: [SnapshotObstruction]
  }
  deriving stock (Eq, Show)

validateContext :: Context -> Either String ()
validateContext context
  | null (contextSnapshotHash context) = Left "empty-snapshot-hash"
  | null (contextAction context) = Left "empty-action"
  | noLeaves (contextTree context) = Left "tree-without-lexical-leaves"
  | any (null . constraintProvenance) (contextConstraints context) =
      Left "empty-constraint-provenance"
  | any
      (`notElem` contextRuleProvenance context)
      (map constraintProvenance (contextConstraints context)) =
      Left "unknown-constraint-provenance"
  | otherwise =
      case invalidAnchor (allAnchors (contextTree context)) of
        Just _ -> Left "invalid-lexical-span"
        Nothing -> Right ()
  where
    noLeaves (LexicalLeaf _ _) = False
    noLeaves (LexicalApply _ children) = null children || all noLeaves children

    invalidAnchor = firstMatching (\anchor -> anchorStart anchor < 0 || anchorEnd anchor <= anchorStart anchor)

contextualFiber :: Snapshot -> [Relation] -> Int -> Context -> Either String [FiberStage]
contextualFiber snapshot relations maxDepth context = do
  validateContext context
  if contextSnapshotHash context /= snapshotHash snapshot
    then Left "snapshot-hash-mismatch"
    else Right ()
  if maxDepth <= 0
    then Left "invalid-max-depth"
    else Right ()
  let kb = snapshotKnowledgeBase snapshot
      initial =
        uniqueCandidates
          [ ContextualCandidate fine []
          | fine <-
              expandFiber
                kb
                FiberQuery
                  { fiberSource = contextSource context
                  , fiberRequirement = HasSort Entity
                  , fiberRelations = relations
                  , fiberMaxDepth = maxDepth
                  }
          ]
      initialStage = FiberStage 0 Nothing initial [] [] []
  pure (initialStage : applyConstraints kb initial 1 (contextConstraints context))
  where
    applyConstraints _ _ _ [] = []
    applyConstraints kb candidates index (constraint : rest) =
      let (matched, misses) = applyConstraint kb constraint candidates
          preference = payloadIsPreference (constraintPayload constraint)
          survivors = if preference then candidates else matched
          stage =
            FiberStage
              index
              (Just constraint)
              survivors
              (if preference then [] else misses)
              (if preference then matched else [])
              (if preference then misses else [])
       in stage : applyConstraints kb survivors (index + 1) rest

applyConstraint ::
  KnowledgeBase ->
  ContextConstraint ->
  [ContextualCandidate] ->
  ([ContextualCandidate], [SnapshotObstruction])
applyConstraint kb constraint =
  foldr step ([], [])
  where
    step candidate (survivors, obstructions) =
      case constraintPayload constraint of
        Requires requirement ->
          case proveRequirement kb target requirement of
            Just proofs ->
              ( candidate
                  { contextualProofs =
                      contextualProofs candidate
                        <> [RequirementConstraintProof constraint proofs]
                  }
                  : survivors
              , obstructions
              )
            Nothing ->
              (survivors, MissingRequirement constraint target : obstructions)
        RequiresRelation relation expectedTarget ->
          case relationProof relation target expectedTarget of
            Just proof ->
              (candidate {contextualProofs = contextualProofs candidate <> [RelationConstraintProof constraint proof]} : survivors, obstructions)
            Nothing ->
              (survivors, MissingRelation constraint target relation expectedTarget : obstructions)
        RequiresSome relation requirement ->
          case relatedProof relation target requirement of
            Just (relationEvidence, requirementEvidence) ->
              ( candidate
                  { contextualProofs =
                      contextualProofs candidate
                        <> [ RelatedConstraintProof
                               constraint
                               relationEvidence
                               requirementEvidence
                           ]
                  }
                  : survivors
              , obstructions
              )
            Nothing ->
              (survivors, MissingRelated constraint target relation requirement : obstructions)
        Prefers requirement ->
          applyRequirement requirement
        PrefersRelation relation expectedTarget ->
          case relationProof relation target expectedTarget of
            Just proof ->
              (candidate {contextualProofs = contextualProofs candidate <> [RelationConstraintProof constraint proof]} : survivors, obstructions)
            Nothing ->
              (survivors, MissingRelation constraint target relation expectedTarget : obstructions)
        PrefersSome relation requirement ->
          applyRelated relation requirement
      where
        target = fineTarget (contextualFineMeaning candidate)

        applyRequirement requirement =
          case proveRequirement kb target requirement of
            Just proofs ->
              ( candidate
                  { contextualProofs =
                      contextualProofs candidate
                        <> [RequirementConstraintProof constraint proofs]
                  }
                  : survivors
              , obstructions
              )
            Nothing ->
              (survivors, MissingRequirement constraint target : obstructions)

        applyRelated relation requirement =
          case relatedProof relation target requirement of
            Just (relationEvidence, requirementEvidence) ->
              ( candidate
                  { contextualProofs =
                      contextualProofs candidate
                        <> [ RelatedConstraintProof
                               constraint
                               relationEvidence
                               requirementEvidence
                           ]
                  }
                  : survivors
              , obstructions
              )
            Nothing ->
              (survivors, MissingRelated constraint target relation requirement : obstructions)

    relationProof relation source target =
      case
          [ assertion
          | assertion <- relationAssertions kb
          , assertedRelation assertion == relation
          , relationSource assertion == source
          , relationTarget assertion == target
          ] of
        assertion : _ ->
          Just (RelationProof relation source target (relationProvenance assertion))
        [] -> Nothing

    relatedProof relation source requirement =
      firstMatchingJust
        [ do
            requirementEvidence <-
              proveRequirement kb (relationTarget assertion) requirement
            pure
              ( RelationProof
                  relation
                  source
                  (relationTarget assertion)
                  (relationProvenance assertion)
              , requirementEvidence
              )
        | assertion <- relationAssertions kb
        , assertedRelation assertion == relation
        , relationSource assertion == source
        ]

stageTargets :: FiberStage -> [EntityId]
stageTargets = map (fineTarget . contextualFineMeaning) . stageCandidates

payloadIsPreference :: ConstraintPayload -> Bool
payloadIsPreference (Prefers _) = True
payloadIsPreference (PrefersRelation _ _) = True
payloadIsPreference (PrefersSome _ _) = True
payloadIsPreference _ = False

uniqueCandidates :: [ContextualCandidate] -> [ContextualCandidate]
uniqueCandidates =
  nubBy
    (\left right -> fineTarget (contextualFineMeaning left) == fineTarget (contextualFineMeaning right))

allAnchors :: LexicalTree -> [LexicalAnchor]
allAnchors (LexicalLeaf anchor _) = [anchor]
allAnchors (LexicalApply _ children) = concatMap allAnchors children

firstMatching :: (value -> Bool) -> [value] -> Maybe value
firstMatching _ [] = Nothing
firstMatching predicate (value : values)
  | predicate value = Just value
  | otherwise = firstMatching predicate values

firstMatchingJust :: [Maybe value] -> Maybe value
firstMatchingJust [] = Nothing
firstMatchingJust (Just value : _) = Just value
firstMatchingJust (Nothing : values) = firstMatchingJust values
