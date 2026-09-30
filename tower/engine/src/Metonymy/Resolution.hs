module Metonymy.Resolution
  ( expandFiber
  , contractTarget
  , verifyCertificate
  , roundTripHolds
  ) where

import qualified Data.Set as Set
import Metonymy.Ontology
import Metonymy.Types

-- | Every entity reachable from the query's own source via the allowed
-- relations (up to fiberMaxDepth hops) that also satisfies the query's
-- requirement. A path's own target can legitimately equal the source
-- again once maxDepth >= 2: outgoingPaths's cycle guard only stops a
-- path from revisiting a node it has already passed *through*, not from
-- landing back on the source itself as a final target (a real
-- possibility whenever the relation set contains a forward/inverse pair
-- over the same underlying property, e.g. LocatedIn/InstitutionOf over
-- Wikidata P131 -- confirmed by a real corpus run, not assumed: raising
-- max_bridge_depth from 1 to 2 surfaced this immediately in production
-- data). The source referring to itself is never a genuine metonymic
-- bridge (that is exactly the literal reading, already handled
-- elsewhere), so it is filtered out here -- the one place every caller
-- (contextualFiber's own initial stage, roundTripHolds) shares.
expandFiber :: KnowledgeBase -> FiberQuery -> [FineMeaning]
expandFiber kb query =
  [ FineMeaning
      { fineTarget = target
      , finePath = path
      , fineRequirementProofs = proofs
      }
  | path <- outgoingPaths kb query
  , let target = pathTarget path
  , target /= fiberSource query
  , Just proofs <- [proveRequirement kb target (fiberRequirement query)]
  ]

contractTarget ::
  KnowledgeBase ->
  Requirement ->
  [Relation] ->
  Int ->
  EntityId ->
  [(CoarseMeaning, FineMeaning)]
contractTarget kb requirement allowed maxDepth target =
  [ ( CoarseMeaning
        { coarseSource = source
        , coarseFiber =
            FiberQuery
              { fiberSource = source
              , fiberRequirement = requirement
              , fiberRelations = allowed
              , fiberMaxDepth = maxDepth
              }
        , coarseLabel = maybe (show source) entityLabel (lookupEntity kb source)
        }
    , FineMeaning
        { fineTarget = target
        , finePath = reversePath
        , fineRequirementProofs = proofs
        }
    )
  | Just proofs <- [proveRequirement kb target requirement]
  , reversePath <- incomingPaths kb allowed maxDepth target
  , let source = pathSource reversePath
    -- Same reasoning as expandFiber's own filter just above: at
    -- maxDepth >= 2, incomingPaths's reverse walk can legitimately land
    -- back on `target` itself as the path's own source whenever the
    -- relation set has a forward/inverse pair over the same property
    -- (confirmed as a real, not just theoretical, occurrence -- a real
    -- CI run of the "reject-contract-*" silver fixtures, which this
    -- module's own maxDepth is shared with via data/contextual-
    -- language-rules.json's "max_bridge_depth", started spuriously
    -- *accepting* contractions this fixture's own gold data expects
    -- rejected, immediately after max_bridge_depth was raised to 2).
    -- `target` contracting into itself is the same tautology
    -- expandFiber already rules out, just in the reverse direction.
  , source /= target
  ]

verifyCertificate :: KnowledgeBase -> Certificate -> Bool
verifyCertificate kb certificate =
  sourceMatches
    && targetMatches
    && pathAllowed
    && all stepExists steps
    && requirementStillProvable
  where
    coarse = certificateCoarse certificate
    fine = certificateFine certificate
    query = coarseFiber coarse
    BridgePath steps = finePath fine

    sourceMatches =
      case steps of
        [] -> fineTarget fine == coarseSource coarse
        firstStep : _ -> bridgeSource firstStep == coarseSource coarse

    targetMatches =
      case reverse steps of
        [] -> fineTarget fine == coarseSource coarse
        lastStep : _ -> bridgeTarget lastStep == fineTarget fine

    pathAllowed =
      length steps <= fiberMaxDepth query
        && all ((`elem` fiberRelations query) . bridgeRelation) steps

    stepExists step =
      any
        ( \assertion ->
            assertedRelation assertion == bridgeRelation step
              && relationSource assertion == bridgeSource step
              && relationTarget assertion == bridgeTarget step
        )
        (relationAssertions kb)

    requirementStillProvable =
      case proveRequirement kb (fineTarget fine) (fiberRequirement query) of
        Just _ -> True
        Nothing -> False

roundTripHolds :: KnowledgeBase -> Certificate -> Bool
roundTripHolds kb certificate =
  verifyCertificate kb certificate
    && fineTarget (certificateFine certificate)
      `elem` map fineTarget (expandFiber kb (coarseFiber (certificateCoarse certificate)))

outgoingPaths :: KnowledgeBase -> FiberQuery -> [BridgePath]
outgoingPaths kb query =
  go
    Set.empty
    (fiberMaxDepth query)
    (fiberSource query)
    []
  where
    go _ 0 _ _ = []
    go visited depth current prefix
      | current `Set.member` visited = []
      | otherwise =
          concatMap extend nextSteps
      where
        visited' = Set.insert current visited
        nextSteps =
          relationStepsFrom kb (fiberRelations query) current
        extend step =
          let newPrefix = prefix <> [step]
           in BridgePath newPrefix
                : go
                  visited'
                  (depth - 1)
                  (bridgeTarget step)
                  newPrefix

incomingPaths ::
  KnowledgeBase ->
  [Relation] ->
  Int ->
  EntityId ->
  [BridgePath]
incomingPaths kb allowed maxDepth target =
  map BridgePath (go Set.empty maxDepth target [])
  where
    go _ 0 _ _ = []
    go visited depth current suffix
      | current `Set.member` visited = []
      | otherwise =
          concatMap extend previousSteps
      where
        visited' = Set.insert current visited
        previousSteps = relationStepsTo kb allowed current
        extend step =
          let newSuffix = step : suffix
           in newSuffix
                : go
                  visited'
                  (depth - 1)
                  (bridgeSource step)
                  newSuffix

pathTarget :: BridgePath -> EntityId
pathTarget (BridgePath []) = error "empty bridge path has no target"
pathTarget (BridgePath steps) = bridgeTarget (last steps)

pathSource :: BridgePath -> EntityId
pathSource (BridgePath []) = error "empty bridge path has no source"
pathSource (BridgePath (step : _)) = bridgeSource step
