{-# OPTIONS --cubical #-}

module Metonymy.ContextualTower where

open import Cubical.Foundations.Prelude
open import Cubical.Data.Empty
open import Cubical.Data.List.Base using (List; []; _∷_)
open import Cubical.Data.Sigma
open import Cubical.Data.Unit
open import Agda.Builtin.Bool
open import Agda.Builtin.String
import Agda.Builtin.Equality as Eq

open import Metonymy.Checker
open import Metonymy.Contextual
import Metonymy.Contextual as Ctx
open import Metonymy.RuntimeBridge
open import Metonymy.EndToEnd
open import Metonymy.Compression
import Metonymy.Compression as Comp
open import Metonymy.Completion
open import Metonymy.Grammar
open import Metonymy.Ontology
import Metonymy.Ontology as Ontology

record BoundConstraint : Type where
  constructor boundConstraint
  field
    boundValue  : ContextConstraint
    originValid : Bool
    originProof : originValid Eq.≡ true

data AllOriginsValid : List BoundConstraint → Type where
  origins[] : AllOriginsValid []
  origins∷ :
    {constraint : BoundConstraint} →
    {constraints : List BoundConstraint} →
    BoundConstraint.originValid constraint Eq.≡ true →
    AllOriginsValid constraints →
    AllOriginsValid (constraint ∷ constraints)

elaborationBindsLexemes :
  (constraints : List BoundConstraint) →
  AllOriginsValid constraints
elaborationBindsLexemes [] = origins[]
elaborationBindsLexemes (constraint ∷ constraints) =
  origins∷
    (BoundConstraint.originProof constraint)
    (elaborationBindsLexemes constraints)

record ContextLayer
  (kb : KnowledgeBase)
  (constraints : List ContextConstraint) : Type where
  constructor contextLayer
  field
    candidate : String
    accepted :
      constraintsHold kb candidate constraints Eq.≡ true

Refines :
  (kb : KnowledgeBase) →
  List ContextConstraint →
  List ContextConstraint →
  Type
Refines kb weaker stronger =
  (candidate : String) →
  constraintsHold kb candidate stronger Eq.≡ true →
  constraintsHold kb candidate weaker Eq.≡ true

fiberRestriction :
  {kb : KnowledgeBase} →
  {weaker stronger : List ContextConstraint} →
  Refines kb weaker stronger →
  ContextLayer kb stronger →
  ContextLayer kb weaker
fiberRestriction refines layer =
  contextLayer
    (ContextLayer.candidate layer)
    (refines (ContextLayer.candidate layer) (ContextLayer.accepted layer))

Extension :
  KnowledgeBase →
  String →
  ContextConstraint →
  Type
Extension = Extends

extensionSound :
  (kb : KnowledgeBase) →
  (candidate : String) →
  (constraint : ContextConstraint) →
  constraintHolds kb candidate constraint Eq.≡ true →
  Extension kb candidate constraint
extensionSound kb candidate constraint checked = checked

extensionComplete :
  (kb : KnowledgeBase) →
  (candidate : String) →
  (constraint : ContextConstraint) →
  Extension kb candidate constraint →
  constraintHolds kb candidate constraint Eq.≡ true
extensionComplete kb candidate constraint extension = extension

obstructionTerminatesPath :
  (kb : KnowledgeBase) →
  (candidate : String) →
  (constraint : ContextConstraint) →
  Obstruction kb candidate constraint →
  Extension kb candidate constraint →
  ⊥
obstructionTerminatesPath = obstructionSound

stagePath :
  (K : Snapshot) →
  (before after : RuntimeClause) →
  (certificateRaw : RawCertificate) →
  (Γ : Ctx.Context) →
  ContextualCertificate K before after certificateRaw Γ →
  Path
    (Completion (RuntimeSystem (Snapshot.snapshotKnowledgeBase K)) clause clause)
    (raw (translate before))
    (raw (translate after))
stagePath K before after certificateRaw Γ certificate =
  hardCellPath
    (checkedRewrite (ContextualCertificate.runtimeCertificate certificate))

record StableStagePath
  (K : Snapshot)
  (before after : RuntimeClause)
  (certificateRaw : RawCertificate)
  (weaker stronger : Ctx.Context)
  (strong : ContextualCertificate K before after certificateRaw stronger) : Type where
  constructor stableStagePath
  field
    sharedRuntimeCell :
      RuntimeAdmissible
        (Snapshot.snapshotKnowledgeBase K)
        before
        after
        certificateRaw

sharedRuntimeCellStability :
  (K : Snapshot) →
  (before after : RuntimeClause) →
  (certificateRaw : RawCertificate) →
  (weaker stronger : Ctx.Context) →
  (certificate : ContextualCertificate K before after certificateRaw stronger) →
  StableStagePath K before after certificateRaw weaker stronger certificate
sharedRuntimeCellStability K before after certificateRaw weaker stronger certificate =
  stableStagePath (ContextualCertificate.runtimeCertificate certificate)

towerPathStability :
  (K : Snapshot) →
  (before after : RuntimeClause) →
  (certificateRaw : RawCertificate) →
  (weaker stronger : Ctx.Context) →
  (weakCertificate : ContextualCertificate K before after certificateRaw weaker) →
  (strongCertificate : ContextualCertificate K before after certificateRaw stronger) →
  ContextualCertificate.runtimeCertificate weakCertificate
    ≡ ContextualCertificate.runtimeCertificate strongCertificate →
  stagePath K before after certificateRaw weaker weakCertificate
    ≡ stagePath K before after certificateRaw stronger strongCertificate
towerPathStability
  K before after certificateRaw weaker stronger
  weakCertificate strongCertificate coherence =
  cong
    (λ admitted → hardCellPath (checkedRewrite admitted))
    coherence

compatibleCandidatesGlue :
  {O : OntologySignature} →
  {R : ResolutionSignature O} →
  {C : CompressionSignature O R} →
  {Γ : Ontology.Context R} →
  {K : Ontology.Hole R} →
  {source : Ontology.Entity O} →
  (left right : Fine {O = O} {R = R} Γ K source) →
  SameMetonymicClass C left right →
  Comp.contract {C = C} left ≡ Comp.contract {C = C} right
compatibleCandidatesGlue {C = C} left right witness =
  Comp.glue {C = C} left right witness

data _∈_ {A : Type} (value : A) : List A → Type where
  here : {values : List A} → value ∈ (value ∷ values)
  there : {other : A} {values : List A} → value ∈ values → value ∈ (other ∷ values)

emptyFiberNoRewrite :
  {A : Type} →
  {candidatePath : A} →
  candidatePath ∈ [] →
  ⊥
emptyFiberNoRewrite ()
