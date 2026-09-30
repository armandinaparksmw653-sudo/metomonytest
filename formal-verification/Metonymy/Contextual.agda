{-# OPTIONS --cubical #-}

module Metonymy.Contextual where

open import Agda.Builtin.Bool
open import Agda.Builtin.Equality
open import Agda.Builtin.List
open import Agda.Builtin.String
open import Cubical.Data.Empty
open import Cubical.Data.Sum.Base

open import Metonymy.Checker
open import Metonymy.RuntimeBridge

sym : {A : Set} {left right : A} → left ≡ right → right ≡ left
sym refl = refl

trans : {A : Set} {left middle right : A} → left ≡ middle → middle ≡ right → left ≡ right
trans refl proof = proof

data ConstraintPayload : Set where
  requires : Requirement → ConstraintPayload
  requiresRelation : String → String → ConstraintPayload
  requiresSome : String → Requirement → ConstraintPayload
  prefers : Requirement → ConstraintPayload
  prefersRelation : String → String → ConstraintPayload
  prefersSome : String → Requirement → ConstraintPayload

record LexicalAnchor : Set where
  constructor lexicalAnchor
  field
    anchorConstructor : String
    anchorLemma : String
    anchorSurface : String

record ContextConstraint : Set where
  constructor contextConstraint
  field
    constraintOrigin : LexicalAnchor
    constraintPayload : ConstraintPayload
    constraintProvenance : String

record Context : Set where
  constructor context
  field
    contextSnapshotHash : String
    contextAction : String
    contextConstraints : List ContextConstraint

record Snapshot : Set where
  constructor snapshot
  field
    snapshotHash : String
    snapshotKnowledgeBase : KnowledgeBase

open ContextConstraint

constraintHolds :
  KnowledgeBase →
  String →
  ContextConstraint →
  Bool
constraintHolds kb candidate constraint with constraintPayload constraint
... | requires requirement =
  not (stringEqual (constraintProvenance constraint) "")
    and satisfiesRequirement kb candidate requirement
... | requiresRelation relation target =
  not (stringEqual (constraintProvenance constraint) "")
    and relationExists kb (edge relation candidate target)
... | requiresSome relation requirement =
  not (stringEqual (constraintProvenance constraint) "")
    and any matches (KnowledgeBase.relationFacts kb)
  where
  matches : RelationFact → Bool
  matches fact =
    stringEqual relation (RelationFact.factRelation fact)
      and stringEqual candidate (RelationFact.factSource fact)
      and satisfiesRequirement kb (RelationFact.factTarget fact) requirement
... | prefers _ =
  not (stringEqual (constraintProvenance constraint) "")
... | prefersRelation _ _ =
  not (stringEqual (constraintProvenance constraint) "")
... | prefersSome _ _ =
  not (stringEqual (constraintProvenance constraint) "")

constraintsHold :
  KnowledgeBase →
  String →
  List ContextConstraint →
  Bool
constraintsHold kb candidate [] = true
constraintsHold kb candidate (constraint ∷ constraints) =
  constraintHolds kb candidate constraint
    and constraintsHold kb candidate constraints

contextValid : Snapshot → Context → Bool
contextValid K Γ =
  not (stringEqual (Context.contextSnapshotHash Γ) "")
    and not (stringEqual (Context.contextAction Γ) "")
    and stringEqual
      (Snapshot.snapshotHash K)
      (Context.contextSnapshotHash Γ)

contextualCheck :
  Snapshot →
  RuntimeClause →
  RuntimeClause →
  RawCertificate →
  Context →
  Bool
contextualCheck K before after raw Γ =
  contextValid K Γ
    and runtimeCheck kb before after raw
    and constraintsHold kb (RawCertificate.rawTarget raw) (Context.contextConstraints Γ)
  where
    kb = Snapshot.snapshotKnowledgeBase K

record ContextualCertificate
  (K : Snapshot)
  (before after : RuntimeClause)
  (raw : RawCertificate)
  (Γ : Context) : Set where
  constructor contextualCertificate
  field
    contextValidProof :
      contextValid K Γ ≡ true
    runtimeCertificate :
      RuntimeAdmissible (Snapshot.snapshotKnowledgeBase K) before after raw
    runtimeProof :
      runtimeCheck (Snapshot.snapshotKnowledgeBase K) before after raw ≡ true
    contextProof :
      constraintsHold
        (Snapshot.snapshotKnowledgeBase K)
        (RawCertificate.rawTarget raw)
        (Context.contextConstraints Γ) ≡ true

contextualCheckSound :
  (K : Snapshot) →
  (before after : RuntimeClause) →
  (raw : RawCertificate) →
  (Γ : Context) →
  contextualCheck K before after raw Γ ≡ true →
  ContextualCertificate K before after raw Γ
contextualCheckSound K before after raw Γ checked =
  contextualCertificate
    validChecked
    (runtimeCheckSound kb before after raw runtimeChecked)
    runtimeChecked
    contextChecked
  where
    kb = Snapshot.snapshotKnowledgeBase K

    validChecked :
      contextValid K Γ ≡ true
    validChecked =
      andTrueLeft
        {left = contextValid K Γ}
        {right =
          runtimeCheck kb before after raw
            and constraintsHold kb (RawCertificate.rawTarget raw) (Context.contextConstraints Γ)}
        checked

    restChecked :
      ( runtimeCheck kb before after raw
        and constraintsHold kb (RawCertificate.rawTarget raw) (Context.contextConstraints Γ)
      ) ≡ true
    restChecked =
      andTrueRight
        {left = contextValid K Γ}
        {right =
          runtimeCheck kb before after raw
            and constraintsHold kb (RawCertificate.rawTarget raw) (Context.contextConstraints Γ)}
        checked

    runtimeChecked :
      runtimeCheck kb before after raw ≡ true
    runtimeChecked =
      andTrueLeft
        {left = runtimeCheck kb before after raw}
        {right = constraintsHold kb (RawCertificate.rawTarget raw) (Context.contextConstraints Γ)}
        restChecked

    contextChecked :
      constraintsHold kb (RawCertificate.rawTarget raw) (Context.contextConstraints Γ) ≡ true
    contextChecked =
      andTrueRight
        {left = runtimeCheck kb before after raw}
        {right = constraintsHold kb (RawCertificate.rawTarget raw) (Context.contextConstraints Γ)}
        restChecked

contextualCheckComplete :
  (K : Snapshot) →
  (before after : RuntimeClause) →
  (raw : RawCertificate) →
  (Γ : Context) →
  ContextualCertificate K before after raw Γ →
  contextualCheck K before after raw Γ ≡ true
contextualCheckComplete K before after raw Γ admitted =
  andOfTrue
    (ContextualCertificate.contextValidProof admitted)
    ( andOfTrue
      (ContextualCertificate.runtimeProof admitted)
      (ContextualCertificate.contextProof admitted)
    )

Extends :
  KnowledgeBase →
  String →
  ContextConstraint →
  Set
Extends kb candidate constraint =
  constraintHolds kb candidate constraint ≡ true

Obstruction :
  KnowledgeBase →
  String →
  ContextConstraint →
  Set
Obstruction kb candidate constraint =
  constraintHolds kb candidate constraint ≡ false

extensionOrObstruction :
  (kb : KnowledgeBase) →
  (candidate : String) →
  (constraint : ContextConstraint) →
  Extends kb candidate constraint ⊎ Obstruction kb candidate constraint
extensionOrObstruction kb candidate constraint with constraintHolds kb candidate constraint
... | true = inl refl
... | false = inr refl

obstructionSound :
  (kb : KnowledgeBase) →
  (candidate : String) →
  (constraint : ContextConstraint) →
  Obstruction kb candidate constraint →
  Extends kb candidate constraint → ⊥
obstructionSound kb candidate constraint obstruction extension =
  trueNotFalse (trans (sym extension) obstruction)
  where
    trueNotFalse : true ≡ false → ⊥
    trueNotFalse ()

contextualPath :
  (K : Snapshot) →
  (before after : RuntimeClause) →
  (raw : RawCertificate) →
  (Γ : Context) →
  (checked : contextualCheck K before after raw Γ ≡ true) →
  _
contextualPath K before after raw Γ checked =
  checkedRuntimePath kb before after raw
    ( andTrueLeft
      {left = runtimeCheck kb before after raw}
      {right = constraintsHold kb (RawCertificate.rawTarget raw) (Context.contextConstraints Γ)}
      ( andTrueRight
        {left = contextValid K Γ}
        {right =
          runtimeCheck kb before after raw
            and constraintsHold kb (RawCertificate.rawTarget raw) (Context.contextConstraints Γ)}
        checked
      )
    )
  where
    kb = Snapshot.snapshotKnowledgeBase K
