-- | The production tower path: every stage of a Context's constraint list
-- is independently re-verified against compiled Agda's
-- @contextLayerCheck@ (via 'verifyContextLayerWithAgda'), not
-- 'Metonymy.Verified.verifyContextualRuntimeWithAgda''s single combined
-- rewrite+one-layer check -- see that function's own docs for why both
-- exist.
module Metonymy.ContextualChecked
  ( contextualFiberChecked
  , ContextualContraction (..)
  , contextualContractionChecked
  , contextualContractionUnchecked
  , CoarseReading (..)
  , contextualCoarseReading
  ) where

import Metonymy.Contextual
import Metonymy.Ontology (proveRequirement, relationStepsFrom)
import Metonymy.Resolution (contractTarget)
import Metonymy.Types
import Metonymy.Verified
  ( verifyCompatibilityWithAgda
  , verifyContextLayerWithAgda
  , verifyPreferenceLayerWithAgda
  )

contextualFiberChecked ::
  Snapshot ->
  [Relation] ->
  Int ->
  Context ->
  Either String [FiberStage]
contextualFiberChecked snapshot relations maxDepth context = do
  stages <- contextualFiber snapshot relations maxDepth context
  verifyStages stages
  pure stages
  where
    verifyStages [] = Right ()
    verifyStages (stage : rest) = do
      let prefixContext =
            context
              { contextConstraints =
                  take (stageIndex stage) (contextConstraints context)
              }
          acceptedTargets = stageTargets stage
          rejectedTargets = map obstructionTarget (stageObstructions stage)
          preferredTargets =
            map
              (fineTarget . contextualFineMeaning)
              (stagePreferredCandidates stage)
          preferenceMissTargets =
            map obstructionTarget (stagePreferenceMisses stage)
      if all (verifyContextLayerWithAgda snapshot prefixContext) acceptedTargets
        then Right ()
        else Left ("agda-rejected-survivor-at-stage-" <> show (stageIndex stage))
      if all
          (not . verifyContextLayerWithAgda snapshot prefixContext)
          rejectedTargets
        then Right ()
        else Left ("agda-accepted-obstruction-at-stage-" <> show (stageIndex stage))
      case stageConstraint stage of
        Just constraint
          | payloadIsPreference (constraintPayload constraint) -> do
              if all
                  (verifyPreferenceLayerWithAgda snapshot constraint)
                  preferredTargets
                then Right ()
                else Left ("agda-rejected-preference-at-stage-" <> show (stageIndex stage))
              if all
                  (not . verifyPreferenceLayerWithAgda snapshot constraint)
                  preferenceMissTargets
                then Right ()
                else Left ("agda-accepted-preference-miss-at-stage-" <> show (stageIndex stage))
        _ -> Right ()
      verifyStages rest

obstructionTarget :: SnapshotObstruction -> EntityId
obstructionTarget (MissingRequirement _ candidate) = candidate
obstructionTarget (MissingRelation _ candidate _ _) = candidate
obstructionTarget (MissingRelated _ candidate _ _) = candidate

data ContextualContraction = ContextualContraction
  { contractionStages :: [FiberStage]
  , contractionSource :: EntityId
  , contractionTarget :: EntityId
  , contractionSafety :: String
  }
  deriving stock (Eq, Show)

contextualContractionChecked ::
  Snapshot ->
  [Relation] ->
  Int ->
  Context ->
  EntityId ->
  Either String ContextualContraction
contextualContractionChecked snapshot relations maxDepth context target = do
  stages <-
    contextualFiberChecked snapshot relations maxDepth context
  finishContraction snapshot relations maxDepth context target stages

contextualContractionUnchecked ::
  Snapshot ->
  [Relation] ->
  Int ->
  Context ->
  EntityId ->
  Either String ContextualContraction
contextualContractionUnchecked snapshot relations maxDepth context target = do
  stages <- contextualFiber snapshot relations maxDepth context
  finishContraction snapshot relations maxDepth context target stages

finishContraction ::
  Snapshot ->
  [Relation] ->
  Int ->
  Context ->
  EntityId ->
  [FiberStage] ->
  Either String ContextualContraction
finishContraction snapshot relations maxDepth context target stages = do
  finalStage <-
    case reverse stages of
      stage : _ -> Right stage
      [] -> Left "empty-contextual-tower"
  let kb = snapshotKnowledgeBase snapshot
      finalTargets = stageTargets finalStage
      missingStages =
        [ stageIndex stage
        | stage <- stages
        , target `notElem` stageTargets stage
        ]
      generic =
        case proveRequirement kb target (HasSort GenericReading) of
          Just _ -> True
          Nothing -> False
      uniqueEntity =
        case finalTargets of
          [only] -> only == target
          _ -> False
      reverseBridge =
        any
          (\(coarse, _) -> coarseSource coarse == contextSource context)
          (contractTarget kb (HasSort Entity) relations maxDepth target)
  case missingStages of
    [] -> Right ()
    indexes
      | stageIndex finalStage `elem` indexes ->
          Left "explicit-target-not-in-final-fiber"
      | otherwise ->
          Left ("explicit-target-missing-at-stage-" <> show (head indexes))
  if not (generic || uniqueEntity)
    then
      -- finalTargets are public, stable Wikidata QIDs -- the same safety
      -- class already printed unconditionally throughout this project
      -- (survivors=/obstruction=/etc), never sentence text -- included
      -- here so a real corpus/fixture run can actually see *which*
      -- entities made the fiber ambiguous instead of only knowing that
      -- it was (a real diagnostic gap found investigating the
      -- max_bridge_depth experiment: this reason string alone gave no
      -- way to tell a genuine new ambiguity from a bug).
      Left ("unsafe-contextual-contraction-non-singleton-fiber:" <> show finalTargets)
    else Right ()
  if not reverseBridge
    then Left "no-reverse-bridge-to-source"
    else
      Right
        ContextualContraction
          { contractionStages = stages
          , contractionSource = contextSource context
          , contractionTarget = target
          , contractionSafety =
              if uniqueEntity
                then "unique-contextual-fiber"
                else "generic-reading"
          }

-- | Whether the fiber's final stage -- if it left more than one survivor
-- -- can be honestly reported as one coarse reading rather than an
-- unresolved list. This never competes with narrowing: it only looks at
-- what remains once every constraint the sentence itself supplied has
-- already been applied.
--
-- The final stage must have been narrowed by a single, specific
-- @Requires (HasSort _)@ -- never @AnyOf@/@AllOf@/a negation -- because
-- only a single declared kind guarantees every survivor is genuinely the
-- same *kind* of thing (see Checker.isSingleHasSort's own comment for
-- why a broad disjunction, e.g. Waterloo's "announce" requirement before
-- its narrowing "in physics" signal, must never be treated this way).
-- Every survivor must also have been reached from the context's source
-- by the same single bridge relation, and every pairing is independently
-- re-verified against the compiled Agda @compatibilityCheck@ -- this
-- function only ever *proposes* a coarse reading; Agda decides.
data CoarseReading = CoarseReading
  { coarseReadingSort :: Sort
  , coarseReadingMembers :: [EntityId]
  }
  deriving stock (Eq, Show)

contextualCoarseReading ::
  Snapshot ->
  [Relation] ->
  Context ->
  [FiberStage] ->
  Maybe CoarseReading
contextualCoarseReading snapshot relations context stages = do
  finalStage <- case reverse stages of
    stage : _ -> Just stage
    [] -> Nothing
  constraint <- stageConstraint finalStage
  sort <- case constraintPayload constraint of
    Requires (HasSort candidateSort) -> Just candidateSort
    _ -> Nothing
  case stageTargets finalStage of
    targets@(_ : _ : _) -> do
      let kb = snapshotKnowledgeBase snapshot
          steps = relationStepsFrom kb relations (contextSource context)
          relationTo t =
            case [bridgeRelation step | step <- steps, bridgeTarget step == t] of
              relation : _ -> Just relation
              [] -> Nothing
      pairs <- traverse (\t -> (,) t <$> relationTo t) targets
      case pairs of
        [] -> Nothing
        (firstTarget, firstRelation) : _ ->
          if all
              ( \(target, relation) ->
                  verifyCompatibilityWithAgda
                    (HasSort sort)
                    (contextSource context)
                    firstRelation
                    firstTarget
                    relation
                    target
              )
              pairs
            then Just (CoarseReading sort targets)
            else Nothing
    _ -> Nothing
