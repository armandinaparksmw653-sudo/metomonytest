module Metonymy.Ontology
  ( KnowledgeBase (..)
  , EntityInfo (..)
  , TypeAssertion (..)
  , RelationAssertion (..)
  , lookupEntity
  , proveRequirement
  , relationStepsFrom
  , relationStepsTo
  ) where

import Data.List (find)
import qualified Data.Set as Set
import Metonymy.Types

data EntityInfo = EntityInfo
  { entityId :: EntityId
  , entityLabel :: String
  , entityGF :: String
  }
  deriving stock (Eq, Show)

data TypeAssertion = TypeAssertion
  { typedEntity :: EntityId
  , assertedSort :: Sort
  , typeProvenance :: Provenance
  }
  deriving stock (Eq, Show)

data RelationAssertion = RelationAssertion
  { assertedRelation :: Relation
  , relationSource :: EntityId
  , relationTarget :: EntityId
  , relationProvenance :: Provenance
  }
  deriving stock (Eq, Show)

data KnowledgeBase = KnowledgeBase
  { entities :: [EntityInfo]
  , typeAssertions :: [TypeAssertion]
  , relationAssertions :: [RelationAssertion]
  , subsortRules :: [(Sort, Sort, String)]
  }
  deriving stock (Eq, Show)

lookupEntity :: KnowledgeBase -> EntityId -> Maybe EntityInfo
lookupEntity kb identifier = find ((== identifier) . entityId) (entities kb)

proveRequirement :: KnowledgeBase -> EntityId -> Requirement -> Maybe [Proof]
proveRequirement kb identifier (HasSort wanted) =
  (: []) <$> proveSort kb Set.empty identifier wanted
proveRequirement kb identifier (AllOf requirements) =
  concat <$> traverse (proveRequirement kb identifier) requirements
proveRequirement kb identifier (AnyOf requirements) =
  firstJust (map (proveRequirement kb identifier) requirements)
proveRequirement kb identifier (Not requirement) =
  case proveRequirement kb identifier requirement of
    Nothing -> Just []
    Just _ -> Nothing

proveSort :: KnowledgeBase -> Set.Set Sort -> EntityId -> Sort -> Maybe Proof
proveSort kb visited identifier wanted
  | wanted `Set.member` visited = Nothing
  | otherwise =
      firstJust [directProof, firstDerivedProof]
  where
    directProof =
      case
        [ assertion
        | assertion <- typeAssertions kb
        , typedEntity assertion == identifier
        , assertedSort assertion == wanted
        ]
      of
        assertion : _ ->
          Just
            ( TypeProof
                identifier
                wanted
                (typeProvenance assertion)
            )
        [] -> Nothing

    firstDerivedProof =
      firstJust
        [ do
            premiseProof <-
              proveSort kb (Set.insert wanted visited) identifier premise
            pure
              ( TypeProof
                  identifier
                  wanted
                  (DerivedBy ruleName [proofProvenance premiseProof])
              )
        | (premise, conclusion, ruleName) <- subsortRules kb
        , conclusion == wanted
        ]

proofProvenance :: Proof -> Provenance
proofProvenance (TypeProof _ _ provenance) = provenance
proofProvenance (RelationProof _ _ _ provenance) = provenance

firstJust :: [Maybe a] -> Maybe a
firstJust [] = Nothing
firstJust (Just value : _) = Just value
firstJust (Nothing : rest) = firstJust rest

relationStepsFrom :: KnowledgeBase -> [Relation] -> EntityId -> [BridgeStep]
relationStepsFrom kb allowed source =
  [ BridgeStep
      { bridgeRelation = assertedRelation assertion
      , bridgeSource = relationSource assertion
      , bridgeTarget = relationTarget assertion
      , bridgeEvidence =
          RelationProof
            (assertedRelation assertion)
            (relationSource assertion)
            (relationTarget assertion)
            (relationProvenance assertion)
      }
  | assertion <- relationAssertions kb
  , relationSource assertion == source
  , assertedRelation assertion `elem` allowed
  ]

relationStepsTo :: KnowledgeBase -> [Relation] -> EntityId -> [BridgeStep]
relationStepsTo kb allowed target =
  [ BridgeStep
      { bridgeRelation = assertedRelation assertion
      , bridgeSource = relationSource assertion
      , bridgeTarget = relationTarget assertion
      , bridgeEvidence =
          RelationProof
            (assertedRelation assertion)
            (relationSource assertion)
            (relationTarget assertion)
            (relationProvenance assertion)
      }
  | assertion <- relationAssertions kb
  , relationTarget assertion == target
  , assertedRelation assertion `elem` allowed
  ]
