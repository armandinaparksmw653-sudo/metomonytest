module Metonymy.Types where

import Data.List (intercalate)

newtype EntityId = EntityId {unEntityId :: String}
  deriving stock (Eq, Ord)

instance Show EntityId where
  show = unEntityId

data Sort
  = Entity
  | Human
  | Writer
  | LiteraryWork
  | Readable
  | Container
  | Drinkable
  | Place
  | Institution
  | Agent
  | Animate
  | Organization
  | Agreement
  | MusicalWork
  | Audible
  | Film
  | Watchable
  | Food
  | Edible
  | Clothing
  | Wearable
  | Brand
  | HumanGroup
  | Event
  | Artifact
  | Product
  | Producer
  | Content
  | Result
  | Possessor
  | LocatedEntity
  | GenericReading
  | University
  | ResearchInstitution
  | Programme
  | ResearchProgramme
  | ScientificDiscipline
  | CommunicationContent
  | Government
  | PoliticalOrganization
  | BusinessOrganization
  | PoliticalAgreement
  | CommercialAgreement
  | Political
  | Commercial
  | SportsOrganization
  | Newspaper
  deriving stock (Eq, Ord, Show, Read, Enum, Bounded)

data Relation
  = Authored
  | Contains
  | GovernedBy
  | Created
  | ProducedBy
  | InhabitedBy
  | Hosts
  | Produces
  | HomeOf
  | Causes
  | PossessedBy
  | Represents
  | LocatedIn
  | AffiliatedWith
  | MemberOf
  | InstitutionOf
  | Offers
  | Conducts
  | About
  | PlaysInLeague
  deriving stock (Eq, Ord, Show, Read, Enum, Bounded)

data Provenance
  = LocalFact String
  | DerivedBy String [Provenance]
  | DiscourseFact String
  deriving stock (Eq, Show)

data Proof
  = TypeProof EntityId Sort Provenance
  | RelationProof Relation EntityId EntityId Provenance
  deriving stock (Eq, Show)

data Requirement
  = HasSort Sort
  | AllOf [Requirement]
  | AnyOf [Requirement]
  | Not Requirement
  deriving stock (Eq, Show, Read)

data RequirementStrength
  = HardRequirement
  | SelectionalPreference
  deriving stock (Eq, Ord, Show, Read)

data Predicate = Predicate
  { predicateName :: String
  , subjectRequirement :: Requirement
  , objectRequirement :: Requirement
  , gfFunction :: String
  , predicateStrength :: RequirementStrength
  , predicateProvenance :: String
  }
  deriving stock (Eq, Show)

data ActionRoleRequirement = ActionRoleRequirement
  { actionId :: String
  , actionLemma :: String
  , actionFrame :: String
  , actionThematicRole :: String
  , actionHoleRole :: HoleRole
  , actionRequirement :: Requirement
  , actionStrength :: RequirementStrength
  , actionProvenance :: String
  }
  deriving stock (Eq, Show)

data BridgeStep = BridgeStep
  { bridgeRelation :: Relation
  , bridgeSource :: EntityId
  , bridgeTarget :: EntityId
  , bridgeEvidence :: Proof
  }
  deriving stock (Eq, Show)

newtype BridgePath = BridgePath {unBridgePath :: [BridgeStep]}
  deriving stock (Eq, Show)

data FiberQuery = FiberQuery
  { fiberSource :: EntityId
  , fiberRequirement :: Requirement
  , fiberRelations :: [Relation]
  , fiberMaxDepth :: Int
  }
  deriving stock (Eq, Show)

data FineMeaning = FineMeaning
  { fineTarget :: EntityId
  , finePath :: BridgePath
  , fineRequirementProofs :: [Proof]
  }
  deriving stock (Eq, Show)

data CoarseMeaning = CoarseMeaning
  { coarseSource :: EntityId
  , coarseFiber :: FiberQuery
  , coarseLabel :: String
  }
  deriving stock (Eq, Show)

data Direction = Expand | Contract
  deriving stock (Eq, Show)

data HoleRole = SubjectHole | ObjectHole
  deriving stock (Eq, Show, Read)

data ForgetContext = ForgetContext
  { genericWholeFiber :: Bool
  , hasRestrictor :: Bool
  , hasQuantifier :: Bool
  , isPositive :: Bool
  , isUnfocused :: Bool
  , hasAnaphoricDependent :: Bool
  , hasTemporalRestriction :: Bool
  }
  deriving stock (Eq, Show)

defaultForgetContext :: ForgetContext
defaultForgetContext =
  ForgetContext
    { genericWholeFiber = True
    , hasRestrictor = False
    , hasQuantifier = False
    , isPositive = True
    , isUnfocused = True
    , hasAnaphoricDependent = False
    , hasTemporalRestriction = False
    }

data Certificate = Certificate
  { certificateDirection :: Direction
  , certificatePredicate :: Predicate
  , certificateHoleRole :: HoleRole
  , certificateCoarse :: CoarseMeaning
  , certificateFine :: FineMeaning
  , certificateSafeToForget :: Bool
  , certificateForgetContext :: ForgetContext
  }
  deriving stock (Eq, Show)

data Candidate = Candidate
  { candidateSurface :: String
  , candidateSourceTree :: String
  , candidateAbstractTree :: String
  , candidateCertificate :: Certificate
  , candidateScore :: Double
  }
  deriving stock (Eq, Show)

data DiscourseEvidence = TargetSalient
  { evidenceTarget :: EntityId
  , evidenceSource :: String
  }
  deriving stock (Eq, Show)

data Authorization
  = DirectHardPath
  | PreferenceCandidate
  | PromotedPreferencePath DiscourseEvidence
  deriving stock (Eq, Show)

renderBridgePath :: BridgePath -> String
renderBridgePath (BridgePath steps) =
  intercalate " ; " (map renderStep steps)
  where
    renderStep step =
      show (bridgeSource step)
        <> " --"
        <> show (bridgeRelation step)
        <> "--> "
        <> show (bridgeTarget step)
