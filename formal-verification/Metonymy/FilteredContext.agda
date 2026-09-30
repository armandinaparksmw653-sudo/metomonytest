{-# OPTIONS --cubical #-}

module Metonymy.FilteredContext where

open import Cubical.Foundations.Prelude
open import Cubical.Foundations.GroupoidLaws using (rUnit)
open import Cubical.Foundations.Isomorphism
  using (Iso; iso; isoToEquiv)
open import Cubical.Foundations.Equiv using (_≃_; idEquiv)
open import Cubical.Foundations.Univalence using (pathToEquiv)
open import Cubical.Data.Empty
open import Cubical.Data.List.Base using (List; []; _∷_; _++_)
open import Cubical.Data.Sigma
open import Cubical.Data.Sum.Base
open import Cubical.Data.Unit
open import Agda.Builtin.Nat using (Nat)
open import Agda.Builtin.String using (String)
open import Cubical.HITs.SetQuotients.Base
  renaming (_/_ to _/c_; [_] to [_]c; eq/ to eq/c; squash/ to squash/c)
import Cubical.HITs.SetQuotients.Properties as SQ

data Decision (A : Type) : Type where
  yes : A → Decision A
  no  : (A → ⊥) → Decision A

All : {A : Type} → (A → Type) → List A → Type
All P [] = Unit
All P (value ∷ values) = P value × All P values

record PositiveConstraintSystem : Type₁ where
  field
    Entity     : Type
    Constraint : Type
    Bridge     : Entity → Type
    Holds      : Entity → Constraint → Type
    decide     : (entity : Entity) → (constraint : Constraint) →
                 Decision (Holds entity constraint)

open PositiveConstraintSystem public

Context : PositiveConstraintSystem → Type
Context system = List (Constraint system)

Fiber :
  (system : PositiveConstraintSystem) →
  Context system →
  Type
Fiber system Γ =
  Σ[ entity ∈ Entity system ]
    Bridge system entity
    × All (Holds system entity) Γ

candidate :
  (system : PositiveConstraintSystem) →
  {Γ : Context system} →
  Fiber system Γ →
  Entity system
candidate system = fst

record Refinement
  (system : PositiveConstraintSystem)
  (weaker stronger : Context system) : Type where
  constructor refinement
  field
    restrictEvidence :
      (entity : Entity system) →
      All (Holds system entity) stronger →
      All (Holds system entity) weaker

open Refinement public

identityRefinement :
  {system : PositiveConstraintSystem} →
  {Γ : Context system} →
  Refinement system Γ Γ
identityRefinement =
  refinement (λ entity evidence → evidence)

composeRefinement :
  {system : PositiveConstraintSystem} →
  {weak middle strong : Context system} →
  Refinement system weak middle →
  Refinement system middle strong →
  Refinement system weak strong
composeRefinement first second =
  refinement
    (λ entity evidence →
      restrictEvidence first entity
        (restrictEvidence second entity evidence))

restrict :
  {system : PositiveConstraintSystem} →
  {weaker stronger : Context system} →
  Refinement system weaker stronger →
  Fiber system stronger →
  Fiber system weaker
restrict map (entity , bridge , evidence) =
  entity , bridge , restrictEvidence map entity evidence

restrictIdentity :
  {system : PositiveConstraintSystem} →
  {Γ : Context system} →
  (value : Fiber system Γ) →
  restrict {system = system}
    (identityRefinement {system = system} {Γ = Γ}) value ≡ value
restrictIdentity {system} {Γ} (entity , bridge , evidence) = refl

restrictComposition :
  {system : PositiveConstraintSystem} →
  {weak middle strong : Context system} →
  (first : Refinement system weak middle) →
  (second : Refinement system middle strong) →
  (value : Fiber system strong) →
  restrict (composeRefinement first second) value
    ≡ restrict first (restrict second value)
restrictComposition first second (entity , bridge , evidence) = refl

record FilteredFamily (system : PositiveConstraintSystem) : Type₁ where
  field
    Object : Context system → Type
    Map :
      {weaker stronger : Context system} →
      Refinement system weaker stronger →
      Object stronger →
      Object weaker
    mapIdentity :
      {Γ : Context system} →
      (value : Object Γ) →
      Map identityRefinement value ≡ value
    mapComposition :
      {weak middle strong : Context system} →
      (first : Refinement system weak middle) →
      (second : Refinement system middle strong) →
      (value : Object strong) →
      Map (composeRefinement first second) value
        ≡ Map first (Map second value)

fiberFunctor :
  (system : PositiveConstraintSystem) →
  FilteredFamily system
FilteredFamily.Object (fiberFunctor system) =
  Fiber system
FilteredFamily.Map (fiberFunctor system) =
  restrict
FilteredFamily.mapIdentity (fiberFunctor system) =
  restrictIdentity {system = system}
FilteredFamily.mapComposition (fiberFunctor system) =
  restrictComposition {system = system}

extend :
  {system : PositiveConstraintSystem} →
  {Γ : Context system} →
  (constraint : Constraint system) →
  (value : Fiber system Γ) →
  Holds system (candidate system value) constraint →
  Fiber system (constraint ∷ Γ)
extend constraint (entity , bridge , evidence) extension =
  entity , bridge , extension , evidence

forgetHead :
  {system : PositiveConstraintSystem} →
  {Γ : Context system} →
  {constraint : Constraint system} →
  Fiber system (constraint ∷ Γ) →
  Fiber system Γ
forgetHead (entity , bridge , extension , evidence) =
  entity , bridge , evidence

headRefinement :
  {system : PositiveConstraintSystem} →
  {Γ : Context system} →
  {constraint : Constraint system} →
  Refinement system Γ (constraint ∷ Γ)
headRefinement {system} {Γ} {constraint} =
  refinement dropHead
  where
    dropHead :
      (entity : Entity system) →
      All (Holds system entity) (constraint ∷ Γ) →
      All (Holds system entity) Γ
    dropHead entity (extension , evidence) =
      evidence

forgetHeadIsRestriction :
  {system : PositiveConstraintSystem} →
  {Γ : Context system} →
  {constraint : Constraint system} →
  (value : Fiber system (constraint ∷ Γ)) →
  forgetHead {system = system} value
    ≡ restrict {system = system}
        (headRefinement {system = system}) value
forgetHeadIsRestriction {system} (entity , bridge , extension , evidence) =
  refl

ExtensionSpace :
  {system : PositiveConstraintSystem} →
  {Γ : Context system} →
  Constraint system →
  Fiber system Γ →
  Type
ExtensionSpace {system} constraint value =
  Holds system (candidate system value) constraint

RestrictionFiber :
  {system : PositiveConstraintSystem} →
  {Γ : Context system} →
  (constraint : Constraint system) →
  Fiber system Γ →
  Type
RestrictionFiber {system} {Γ} constraint value =
  Σ[ lifted ∈ Fiber system (constraint ∷ Γ) ]
    forgetHead {system = system} lifted ≡ value

extensionToRestrictionFiber :
  {system : PositiveConstraintSystem} →
  {Γ : Context system} →
  (constraint : Constraint system) →
  (value : Fiber system Γ) →
  ExtensionSpace {system = system} constraint value →
  RestrictionFiber {system = system} constraint value
extensionToRestrictionFiber {system} constraint
  (entity , bridge , evidence) extension =
  (entity , bridge , extension , evidence) , refl

restrictionFiberToExtension :
  {system : PositiveConstraintSystem} →
  {Γ : Context system} →
  (constraint : Constraint system) →
  (value : Fiber system Γ) →
  RestrictionFiber {system = system} constraint value →
  ExtensionSpace {system = system} constraint value
restrictionFiberToExtension {system} constraint value
  ((entity , bridge , extension , evidence) , equality) =
  subst
    (λ endpoint → Holds system endpoint constraint)
    (cong (candidate system) equality)
    extension

record LogicalEquivalence (A B : Type) : Type where
  constructor logicalEquivalence
  field
    forward  : A → B
    backward : B → A

extensionIsLiftingProblem :
  {system : PositiveConstraintSystem} →
  {Γ : Context system} →
  (constraint : Constraint system) →
  (value : Fiber system Γ) →
  LogicalEquivalence
    (ExtensionSpace {system = system} constraint value)
    (RestrictionFiber {system = system} constraint value)
extensionIsLiftingProblem {system} constraint value =
  logicalEquivalence
    (extensionToRestrictionFiber {system = system} constraint value)
    (restrictionFiberToExtension {system = system} constraint value)

extensionLiftingEquiv :
  {system : PositiveConstraintSystem} →
  {Γ : Context system} →
  (constraint : Constraint system) →
  (value : Fiber system Γ) →
  isProp (ExtensionSpace {system = system} constraint value) →
  isProp (RestrictionFiber {system = system} constraint value) →
  ExtensionSpace {system = system} constraint value
    ≃ RestrictionFiber {system = system} constraint value
extensionLiftingEquiv {system} constraint value extensionProp liftingProp =
  isoToEquiv
    ( iso
      (extensionToRestrictionFiber {system = system} constraint value)
      (restrictionFiberToExtension {system = system} constraint value)
      (λ lifted →
        liftingProp
          ( extensionToRestrictionFiber {system = system} constraint value
            ( restrictionFiberToExtension {system = system}
              constraint value lifted
            )
          )
          lifted)
      (λ extension →
        extensionProp
          ( restrictionFiberToExtension {system = system} constraint value
            ( extensionToRestrictionFiber {system = system}
              constraint value extension
            )
          )
          extension)
    )

Obstruction :
  {system : PositiveConstraintSystem} →
  {Γ : Context system} →
  Constraint system →
  Fiber system Γ →
  Type
Obstruction {system} constraint value =
  ExtensionSpace {system = system} constraint value → ⊥

extensionOrObstruction :
  {system : PositiveConstraintSystem} →
  {Γ : Context system} →
  (constraint : Constraint system) →
  (value : Fiber system Γ) →
  ExtensionSpace {system = system} constraint value
    ⊎ Obstruction {system = system} constraint value
extensionOrObstruction {system} constraint value
  with decide system (candidate system value) constraint
... | yes extension = inl extension
... | no obstruction = inr obstruction

extensionObstructionDisjoint :
  {system : PositiveConstraintSystem} →
  {Γ : Context system} →
  (constraint : Constraint system) →
  (value : Fiber system Γ) →
  ExtensionSpace {system = system} constraint value →
  Obstruction {system = system} constraint value →
  ⊥
extensionObstructionDisjoint constraint value extension obstruction =
  obstruction extension

record PathSystem (system : PositiveConstraintSystem) : Type₁ where
  field
    Meaning  : Type
    implicit : Meaning
    explicit : Entity system → Meaning
    basePath :
      (entity : Entity system) →
      Bridge system entity →
      implicit ≡ explicit entity

open PathSystem public

StagePath :
  {system : PositiveConstraintSystem} →
  PathSystem system →
  {Γ : Context system} →
  Fiber system Γ →
  Type
StagePath {system} paths value =
  implicit paths ≡ explicit paths (candidate system value)

stagePath :
  {system : PositiveConstraintSystem} →
  (paths : PathSystem system) →
  {Γ : Context system} →
  (value : Fiber system Γ) →
  StagePath {system = system} paths value
stagePath {system} paths (entity , bridge , evidence) =
  basePath paths entity bridge

stagePathNaturality :
  {system : PositiveConstraintSystem} →
  (paths : PathSystem system) →
  {weaker stronger : Context system} →
  (map : Refinement system weaker stronger) →
  (value : Fiber system stronger) →
  stagePath {system = system} paths value
    ≡ stagePath {system = system} paths
        (restrict {system = system} map value)
stagePathNaturality {system} paths map (entity , bridge , evidence) =
  refl

stabilityIdentity :
  {system : PositiveConstraintSystem} →
  (paths : PathSystem system) →
  {Γ : Context system} →
  (value : Fiber system Γ) →
  stagePathNaturality {system = system} paths
    (identityRefinement {system = system}) value ≡ refl
stabilityIdentity {system} paths (entity , bridge , evidence) =
  refl

stabilityComposition :
  {system : PositiveConstraintSystem} →
  (paths : PathSystem system) →
  {weak middle strong : Context system} →
  (first : Refinement system weak middle) →
  (second : Refinement system middle strong) →
  (value : Fiber system strong) →
  stagePathNaturality {system = system} paths
    (composeRefinement first second) value
    ≡
  ( stagePathNaturality {system = system} paths second value
    ∙ stagePathNaturality {system = system} paths first
        (restrict {system = system} second value)
  )
stabilityComposition {system} paths first second (entity , bridge , evidence) =
  rUnit refl

record NaturalStageSection
  {system : PositiveConstraintSystem}
  (paths : PathSystem system) : Type₁ where
  field
    section :
      {Γ : Context system} →
      (value : Fiber system Γ) →
      StagePath {system = system} paths value
    natural :
      {weaker stronger : Context system} →
      (map : Refinement system weaker stronger) →
      (value : Fiber system stronger) →
      section value ≡ section (restrict {system = system} map value)
    identityCoherence :
      {Γ : Context system} →
      (value : Fiber system Γ) →
      natural (identityRefinement {system = system}) value ≡ refl
    compositionCoherence :
      {weak middle strong : Context system} →
      (first : Refinement system weak middle) →
      (second : Refinement system middle strong) →
      (value : Fiber system strong) →
      natural (composeRefinement first second) value
        ≡
      ( natural second value
        ∙ natural first (restrict {system = system} second value)
      )

naturalStageSection :
  {system : PositiveConstraintSystem} →
  (paths : PathSystem system) →
  NaturalStageSection paths
NaturalStageSection.section (naturalStageSection paths) =
  stagePath paths
NaturalStageSection.natural (naturalStageSection paths) =
  stagePathNaturality paths
NaturalStageSection.identityCoherence (naturalStageSection paths) =
  stabilityIdentity paths
NaturalStageSection.compositionCoherence (naturalStageSection paths) =
  stabilityComposition paths

UniqueFiber :
  (system : PositiveConstraintSystem) →
  {Γ : Context system} →
  Fiber system Γ →
  Type
UniqueFiber system {Γ} selected =
  (value : Fiber system Γ) → value ≡ selected

UniqueEntity :
  (system : PositiveConstraintSystem) →
  {Γ : Context system} →
  Fiber system Γ →
  Type
UniqueEntity system {Γ} selected =
  (value : Fiber system Γ) →
  candidate system selected ≡ candidate system value

uniqueFiberImpliesUniqueEntity :
  {system : PositiveConstraintSystem} →
  {Γ : Context system} →
  (selected : Fiber system Γ) →
  UniqueFiber system selected →
  UniqueEntity system selected
uniqueFiberImpliesUniqueEntity {system = system} _ unique value =
  cong (candidate system) (sym (unique value))

uniqueEntityStrengthens :
  {system : PositiveConstraintSystem} →
  {weaker stronger : Context system} →
  (map : Refinement system weaker stronger) →
  (value : Fiber system stronger) →
  UniqueEntity system (restrict {system = system} map value) →
  UniqueEntity system value
uniqueEntityStrengthens {system = system} map value uniqueWeaker strongerValue =
  uniqueWeaker (restrict {system = system} map strongerValue)

record SafeContraction
  {system : PositiveConstraintSystem}
  (paths : PathSystem system)
  {Γ : Context system}
  (selected : Fiber system Γ) : Type where
  field
    uniqueEntity :
      UniqueEntity system selected
    contractionPath :
      explicit paths (candidate system selected)
        ≡ implicit paths

safeContraction :
  {system : PositiveConstraintSystem} →
  (paths : PathSystem system) →
  {Γ : Context system} →
  (selected : Fiber system Γ) →
  UniqueEntity system selected →
  SafeContraction paths selected
SafeContraction.uniqueEntity
  (safeContraction paths selected unique) =
  unique
SafeContraction.contractionPath
  (safeContraction paths selected _) =
  sym (stagePath paths selected)

contractionPathNaturality :
  {system : PositiveConstraintSystem} →
  (paths : PathSystem system) →
  {weaker stronger : Context system} →
  (map : Refinement system weaker stronger) →
  (value : Fiber system stronger) →
  sym (stagePath paths value)
    ≡ sym (stagePath paths (restrict {system = system} map value))
contractionPathNaturality paths map value =
  cong sym (stagePathNaturality paths map value)

record CompatibilitySystem (system : PositiveConstraintSystem) : Type₁ where
  field
    Compatible :
      Entity system →
      Entity system →
      Type

open CompatibilitySystem public

FiberCompatible :
  (system : PositiveConstraintSystem) →
  CompatibilitySystem system →
  {Γ : Context system} →
  Fiber system Γ →
  Fiber system Γ →
  Type
FiberCompatible system compatibility left right =
  Compatible compatibility (candidate system left) (candidate system right)

CoarseFiber :
  {system : PositiveConstraintSystem} →
  CompatibilitySystem system →
  Context system →
  Type
CoarseFiber {system} compatibility Γ =
  Fiber system Γ /c FiberCompatible system compatibility

isSetCoarseFiber :
  {system : PositiveConstraintSystem} →
  {compatibility : CompatibilitySystem system} →
  {Γ : Context system} →
  isSet (CoarseFiber compatibility Γ)
isSetCoarseFiber = squash/c

compress :
  {system : PositiveConstraintSystem} →
  {compatibility : CompatibilitySystem system} →
  {Γ : Context system} →
  Fiber system Γ →
  CoarseFiber compatibility Γ
compress = [_]c

restrictPreservesCompatibility :
  {system : PositiveConstraintSystem} →
  {compatibility : CompatibilitySystem system} →
  {weaker stronger : Context system} →
  (map : Refinement system weaker stronger) →
  {left right : Fiber system stronger} →
  FiberCompatible system compatibility left right →
  FiberCompatible system compatibility
    (restrict {system = system} map left)
    (restrict {system = system} map right)
restrictPreservesCompatibility {system} map witness =
  witness

restrictCoarse :
  {system : PositiveConstraintSystem} →
  {compatibility : CompatibilitySystem system} →
  {weaker stronger : Context system} →
  Refinement system weaker stronger →
  CoarseFiber compatibility stronger →
  CoarseFiber compatibility weaker
restrictCoarse {system} {compatibility = compatibility} map =
  SQ.rec
    (isSetCoarseFiber {system = system} {compatibility = compatibility})
    (λ value →
      compress {system = system} {compatibility = compatibility}
        (restrict {system = system} map value))
    (λ left right witness →
      eq/c
        (restrict {system = system} map left)
        (restrict {system = system} map right)
        (restrictPreservesCompatibility
          {system = system}
          {compatibility = compatibility}
          map
          {left = left}
          {right = right}
          witness))

compressionNaturality :
  {system : PositiveConstraintSystem} →
  {compatibility : CompatibilitySystem system} →
  {weaker stronger : Context system} →
  (map : Refinement system weaker stronger) →
  (value : Fiber system stronger) →
  restrictCoarse {system = system} {compatibility = compatibility}
    map (compress {system = system} {compatibility = compatibility} value)
    ≡ compress {system = system} {compatibility = compatibility}
        (restrict {system = system} map value)
compressionNaturality {system} map value =
  refl

coarseRestrictionIdentity :
  {system : PositiveConstraintSystem} →
  {compatibility : CompatibilitySystem system} →
  {Γ : Context system} →
  (value : CoarseFiber compatibility Γ) →
  restrictCoarse {system = system} {compatibility = compatibility}
    (identityRefinement {system = system}) value
    ≡ value
coarseRestrictionIdentity {system} {compatibility = compatibility} =
  SQ.elimProp
    (λ value →
      isSetCoarseFiber {system = system} {compatibility = compatibility} _ _)
    (λ value → refl)

coarseRestrictionComposition :
  {system : PositiveConstraintSystem} →
  {compatibility : CompatibilitySystem system} →
  {weak middle strong : Context system} →
  (first : Refinement system weak middle) →
  (second : Refinement system middle strong) →
  (value : CoarseFiber compatibility strong) →
  restrictCoarse {system = system} {compatibility = compatibility}
    (composeRefinement {system = system} first second) value
    ≡
  restrictCoarse {system = system} {compatibility = compatibility} first
    (restrictCoarse {system = system} {compatibility = compatibility}
      second value)
coarseRestrictionComposition
  {system} {compatibility = compatibility} first second =
  SQ.elimProp
    (λ value →
      isSetCoarseFiber {system = system} {compatibility = compatibility} _ _)
    (λ value → refl)

record ContextualHomotopyTower
  (system : PositiveConstraintSystem)
  (paths : PathSystem system)
  (compatibility : CompatibilitySystem system) : Type₁ where
  field
    filteredFibers :
      FilteredFamily system
    naturalPaths :
      NaturalStageSection paths
    liftingDecision :
      {Γ : Context system} →
      (constraint : Constraint system) →
      (value : Fiber system Γ) →
      ExtensionSpace {system = system} constraint value
        ⊎ Obstruction {system = system} constraint value
    coarseRestriction :
      {weaker stronger : Context system} →
      Refinement system weaker stronger →
      CoarseFiber compatibility stronger →
      CoarseFiber compatibility weaker
    coarseIdentity :
      {Γ : Context system} →
      (value : CoarseFiber compatibility Γ) →
      coarseRestriction identityRefinement value ≡ value
    coarseComposition :
      {weak middle strong : Context system} →
      (first : Refinement system weak middle) →
      (second : Refinement system middle strong) →
      (value : CoarseFiber compatibility strong) →
      coarseRestriction (composeRefinement first second) value
        ≡ coarseRestriction first (coarseRestriction second value)
    compressionCommutes :
      {weaker stronger : Context system} →
      (map : Refinement system weaker stronger) →
      (value : Fiber system stronger) →
      coarseRestriction map
        (compress {system = system} {compatibility = compatibility} value)
        ≡
      compress {system = system} {compatibility = compatibility}
        (restrict {system = system} map value)

contextualHomotopyTower :
  (system : PositiveConstraintSystem) →
  (paths : PathSystem system) →
  (compatibility : CompatibilitySystem system) →
  ContextualHomotopyTower system paths compatibility
ContextualHomotopyTower.filteredFibers
  (contextualHomotopyTower system paths compatibility) =
  fiberFunctor system
ContextualHomotopyTower.naturalPaths
  (contextualHomotopyTower system paths compatibility) =
  naturalStageSection paths
ContextualHomotopyTower.liftingDecision
  (contextualHomotopyTower system paths compatibility) =
  extensionOrObstruction {system = system}
ContextualHomotopyTower.coarseRestriction
  (contextualHomotopyTower system paths compatibility) =
  restrictCoarse {compatibility = compatibility}
ContextualHomotopyTower.coarseIdentity
  (contextualHomotopyTower system paths compatibility) =
  coarseRestrictionIdentity {compatibility = compatibility}
ContextualHomotopyTower.coarseComposition
  (contextualHomotopyTower system paths compatibility) =
  coarseRestrictionComposition {compatibility = compatibility}
ContextualHomotopyTower.compressionCommutes
  (contextualHomotopyTower system paths compatibility) =
  compressionNaturality {compatibility = compatibility}

SystemContext : Type₁
SystemContext =
  Σ[ system ∈ PositiveConstraintSystem ] Context system

FiberAt :
  SystemContext →
  Type
FiberAt (system , Γ) =
  Fiber system Γ

snapshotSystemTransport :
  (first second : SystemContext) →
  first ≡ second →
  FiberAt first ≃ FiberAt second
snapshotSystemTransport first second equality =
  pathToEquiv (cong FiberAt equality)

data LexicalTree (Constraint : Type) : Type where
  lexicalLeaf :
    (gfConstructor lemma surface : String) →
    (start end : Nat) →
    List Constraint →
    LexicalTree Constraint
  lexicalApply :
    String →
    List (LexicalTree Constraint) →
    LexicalTree Constraint

collectConstraints :
  {Constraint : Type} →
  LexicalTree Constraint →
  List Constraint
collectConstraints (lexicalLeaf gfConstructor lemma surface start end constraints) =
  constraints
collectConstraints (lexicalApply gfConstructor children) =
  collectChildren children
  where
    collectChildren : List (LexicalTree _) → List _
    collectChildren [] = []
    collectChildren (child ∷ children) =
      collectConstraints child ++ collectChildren children

elaborate :
  {Constraint : Type} →
  LexicalTree Constraint →
  List Constraint
elaborate =
  collectConstraints

elaborationExact :
  {Constraint : Type} →
  (tree : LexicalTree Constraint) →
  elaborate tree ≡ collectConstraints tree
elaborationExact tree =
  refl

data GFCategory : Type where
  sentence nounPhrase verbPhrase transitiveVerb
    commonNoun adjective prepositionalPhrase : GFCategory

record LexicalAnchor : Type where
  constructor lexicalAnchor
  field
    gfConstructor : String
    lemma         : String
    surface       : String
    start         : Nat
    end           : Nat

data PositiveGFTree (Payload : Type) : GFCategory → Type where
  gfLeaf :
    {category : GFCategory} →
    LexicalAnchor →
    List Payload →
    PositiveGFTree Payload category
  gfPred :
    PositiveGFTree Payload nounPhrase →
    PositiveGFTree Payload verbPhrase →
    PositiveGFTree Payload sentence
  gfCompl :
    PositiveGFTree Payload transitiveVerb →
    PositiveGFTree Payload nounPhrase →
    PositiveGFTree Payload verbPhrase
  gfInPP :
    PositiveGFTree Payload nounPhrase →
    PositiveGFTree Payload prepositionalPhrase
  gfAboutPP :
    PositiveGFTree Payload nounPhrase →
    PositiveGFTree Payload prepositionalPhrase
  gfWithPP :
    PositiveGFTree Payload nounPhrase →
    PositiveGFTree Payload prepositionalPhrase
  gfForPP :
    PositiveGFTree Payload nounPhrase →
    PositiveGFTree Payload prepositionalPhrase
  gfModifyNP :
    PositiveGFTree Payload nounPhrase →
    PositiveGFTree Payload prepositionalPhrase →
    PositiveGFTree Payload nounPhrase
  gfModifyRel :
    PositiveGFTree Payload nounPhrase →
    PositiveGFTree Payload transitiveVerb →
    PositiveGFTree Payload nounPhrase →
    PositiveGFTree Payload nounPhrase
  gfModifyRelCN :
    PositiveGFTree Payload commonNoun →
    PositiveGFTree Payload transitiveVerb →
    PositiveGFTree Payload nounPhrase →
    PositiveGFTree Payload commonNoun
  gfAdjCN :
    PositiveGFTree Payload adjective →
    PositiveGFTree Payload commonNoun →
    PositiveGFTree Payload commonNoun
  gfDefNP :
    PositiveGFTree Payload commonNoun →
    PositiveGFTree Payload nounPhrase
  gfIndefNP :
    PositiveGFTree Payload commonNoun →
    PositiveGFTree Payload nounPhrase
  gfEveryNP :
    PositiveGFTree Payload commonNoun →
    PositiveGFTree Payload nounPhrase

collectGFConstraints :
  {Payload : Type} →
  {category : GFCategory} →
  PositiveGFTree Payload category →
  List Payload
collectGFConstraints (gfLeaf anchor payloads) =
  payloads
collectGFConstraints (gfPred subject predicate) =
  collectGFConstraints subject ++ collectGFConstraints predicate
collectGFConstraints (gfCompl verb object) =
  collectGFConstraints verb ++ collectGFConstraints object
collectGFConstraints (gfInPP object) =
  collectGFConstraints object
collectGFConstraints (gfAboutPP object) =
  collectGFConstraints object
collectGFConstraints (gfWithPP object) =
  collectGFConstraints object
collectGFConstraints (gfForPP object) =
  collectGFConstraints object
collectGFConstraints (gfModifyNP head modifier) =
  collectGFConstraints head ++ collectGFConstraints modifier
collectGFConstraints (gfModifyRel head verb object) =
  collectGFConstraints head
    ++ collectGFConstraints verb
    ++ collectGFConstraints object
collectGFConstraints (gfModifyRelCN head verb object) =
  collectGFConstraints head
    ++ collectGFConstraints verb
    ++ collectGFConstraints object
collectGFConstraints (gfAdjCN modifier head) =
  collectGFConstraints modifier ++ collectGFConstraints head
collectGFConstraints (gfDefNP noun) =
  collectGFConstraints noun
collectGFConstraints (gfIndefNP noun) =
  collectGFConstraints noun
collectGFConstraints (gfEveryNP noun) =
  collectGFConstraints noun

elaboratePositiveGF :
  {Payload : Type} →
  PositiveGFTree Payload sentence →
  List Payload
elaboratePositiveGF =
  collectGFConstraints

gfElaborationExact :
  {Payload : Type} →
  (tree : PositiveGFTree Payload sentence) →
  elaboratePositiveGF tree ≡ collectGFConstraints tree
gfElaborationExact tree =
  refl

record RuleSnapshot : Type₁ where
  field
    RuleId : Type
    ContainsRule : RuleId → Type

open RuleSnapshot public

record CertifiedConstraint
  (rules : RuleSnapshot)
  (Payload : Type) : Type where
  constructor certifiedConstraint
  field
    payload : Payload
    ruleId  : RuleId rules
    ruleMembership : ContainsRule rules ruleId

open CertifiedConstraint public

allConstraintsCertified :
  {rules : RuleSnapshot} →
  {Payload : Type} →
  (constraints : List (CertifiedConstraint rules Payload)) →
  All
    (λ constraint →
      ContainsRule rules (ruleId constraint))
    constraints
allConstraintsCertified [] =
  tt
allConstraintsCertified (constraint ∷ constraints) =
  ruleMembership constraint ,
  allConstraintsCertified constraints

gfElaborationCertified :
  {rules : RuleSnapshot} →
  {Payload : Type} →
  (tree : PositiveGFTree
    (CertifiedConstraint rules Payload)
    sentence) →
  All
    (λ constraint →
      ContainsRule rules (ruleId constraint))
    (elaboratePositiveGF tree)
gfElaborationCertified tree =
  allConstraintsCertified (elaboratePositiveGF tree)
