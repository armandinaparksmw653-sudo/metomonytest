{-# OPTIONS --cubical #-}

module Metonymy.FilteredRuntime where

open import Cubical.Foundations.Prelude
open import Cubical.Data.List.Base using (List; []; _∷_)
open import Cubical.Data.Unit using (Unit; tt)
open import Agda.Builtin.Bool
open import Agda.Builtin.String
import Agda.Builtin.Equality as Eq

open import Metonymy.Checker
open import Metonymy.FilteredContext
open import Metonymy.RuntimeBridge
open import Metonymy.EndToEnd
open import Metonymy.Completion

open RawContextConstraint

singleConstraintCheck :
  KnowledgeBase →
  String →
  RawContextConstraint →
  Bool
singleConstraintCheck kb entity constraint =
  anchorValid (rawConstraintOrigin constraint)
    and not (stringEqual (rawConstraintProvenance constraint) "")
    and rawConstraintHolds kb entity constraint

runtimeDecision :
  (kb : KnowledgeBase) →
  (entity : String) →
  (constraint : RawContextConstraint) →
  Decision
    (singleConstraintCheck kb entity constraint Eq.≡ true)
runtimeDecision kb entity constraint
  with singleConstraintCheck kb entity constraint
... | true = yes Eq.refl
... | false = no (λ ())

runtimePositiveSystem :
  KnowledgeBase →
  PositiveConstraintSystem
Entity (runtimePositiveSystem kb) =
  String
Constraint (runtimePositiveSystem kb) =
  RawContextConstraint
Bridge (runtimePositiveSystem kb) entity =
  Unit
Holds (runtimePositiveSystem kb) entity constraint =
  singleConstraintCheck kb entity constraint Eq.≡ true
decide (runtimePositiveSystem kb) =
  runtimeDecision kb

allRuntimeConstraintsSound :
  (kb : KnowledgeBase) →
  (entity : String) →
  (constraints : List RawContextConstraint) →
  All
    (Holds (runtimePositiveSystem kb) entity)
    constraints →
  rawConstraintsHold kb entity constraints Eq.≡ true
allRuntimeConstraintsSound kb entity [] evidence =
  Eq.refl
allRuntimeConstraintsSound kb entity
  (constraint ∷ constraints)
  (singleProof , restProof) =
  andOfTrue
    anchorProof
    ( andOfTrue
      provenanceProof
      ( andOfTrue
        payloadProof
        (allRuntimeConstraintsSound kb entity constraints restProof)
      )
    )
  where
    anchorProof :
      anchorValid (rawConstraintOrigin constraint) Eq.≡ true
    anchorProof =
      andTrueLeft
        {left = anchorValid (rawConstraintOrigin constraint)}
        {right =
          not (stringEqual (rawConstraintProvenance constraint) "")
            and rawConstraintHolds kb entity constraint}
        singleProof

    afterAnchor :
      ( not (stringEqual (rawConstraintProvenance constraint) "")
        and rawConstraintHolds kb entity constraint
      ) Eq.≡ true
    afterAnchor =
      andTrueRight
        {left = anchorValid (rawConstraintOrigin constraint)}
        {right =
          not (stringEqual (rawConstraintProvenance constraint) "")
            and rawConstraintHolds kb entity constraint}
        singleProof

    provenanceProof :
      not (stringEqual (rawConstraintProvenance constraint) "") Eq.≡ true
    provenanceProof =
      andTrueLeft afterAnchor

    payloadProof :
      rawConstraintHolds kb entity constraint Eq.≡ true
    payloadProof =
      andTrueRight afterAnchor

checkerConstraintsComplete :
  (kb : KnowledgeBase) →
  (entity : String) →
  (constraints : List RawContextConstraint) →
  rawConstraintsHold kb entity constraints Eq.≡ true →
  All
    (Holds (runtimePositiveSystem kb) entity)
    constraints
checkerConstraintsComplete kb entity [] checked =
  tt
checkerConstraintsComplete kb entity
  (constraint ∷ constraints)
  checked =
  singleProof ,
  checkerConstraintsComplete kb entity constraints restProof
  where
    anchorProof :
      anchorValid (rawConstraintOrigin constraint) Eq.≡ true
    anchorProof =
      andTrueLeft
        {left = anchorValid (rawConstraintOrigin constraint)}
        {right =
          not (stringEqual (rawConstraintProvenance constraint) "")
            and rawConstraintHolds kb entity constraint
            and rawConstraintsHold kb entity constraints}
        checked

    afterAnchor :
      ( not (stringEqual (rawConstraintProvenance constraint) "")
        and rawConstraintHolds kb entity constraint
        and rawConstraintsHold kb entity constraints
      ) Eq.≡ true
    afterAnchor =
      andTrueRight
        {left = anchorValid (rawConstraintOrigin constraint)}
        {right =
          not (stringEqual (rawConstraintProvenance constraint) "")
            and rawConstraintHolds kb entity constraint
            and rawConstraintsHold kb entity constraints}
        checked

    provenanceProof :
      not (stringEqual (rawConstraintProvenance constraint) "") Eq.≡ true
    provenanceProof =
      andTrueLeft
        {left = not (stringEqual (rawConstraintProvenance constraint) "")}
        {right =
          rawConstraintHolds kb entity constraint
            and rawConstraintsHold kb entity constraints}
        afterAnchor

    afterProvenance :
      ( rawConstraintHolds kb entity constraint
        and rawConstraintsHold kb entity constraints
      ) Eq.≡ true
    afterProvenance =
      andTrueRight
        {left = not (stringEqual (rawConstraintProvenance constraint) "")}
        {right =
          rawConstraintHolds kb entity constraint
            and rawConstraintsHold kb entity constraints}
        afterAnchor

    payloadProof :
      rawConstraintHolds kb entity constraint Eq.≡ true
    payloadProof =
      andTrueLeft afterProvenance

    restProof :
      rawConstraintsHold kb entity constraints Eq.≡ true
    restProof =
      andTrueRight afterProvenance

    singleProof :
      singleConstraintCheck kb entity constraint Eq.≡ true
    singleProof =
      andOfTrue anchorProof
        (andOfTrue provenanceProof payloadProof)

record _↔_ (A B : Type) : Type where
  constructor logicalEquivalence
  field
    forward  : A → B
    backward : B → A

runtimeFiberCheckerEquivalence :
  (kb : KnowledgeBase) →
  (entity : String) →
  (constraints : List RawContextConstraint) →
  All
    (Holds (runtimePositiveSystem kb) entity)
    constraints
  ↔
  (rawConstraintsHold kb entity constraints Eq.≡ true)
runtimeFiberCheckerEquivalence kb entity constraints =
  logicalEquivalence
    (allRuntimeConstraintsSound kb entity constraints)
    (checkerConstraintsComplete kb entity constraints)

record RuntimeCandidate
  (kb : KnowledgeBase)
  (before : RuntimeClause) : Type where
  constructor runtimeCandidate
  field
    candidateAfter       : RuntimeClause
    candidateCertificate : RawCertificate

open RuntimeCandidate public

runtimeCandidateDecision :
  (kb : KnowledgeBase) →
  (before : RuntimeClause) →
  (rules : List String) →
  (candidate : RuntimeCandidate kb before) →
  (constraint : RawContextConstraint) →
  Decision
    ( ( singleConstraintCheck
        kb
        (RawCertificate.rawTarget (candidateCertificate candidate))
        constraint
        and any
          (stringEqual (rawConstraintProvenance constraint))
          rules
      )
      Eq.≡ true
    )
runtimeCandidateDecision kb before rules candidate constraint
  with
    singleConstraintCheck
      kb
      (RawCertificate.rawTarget (candidateCertificate candidate))
      constraint
      and any
        (stringEqual (rawConstraintProvenance constraint))
        rules
... | true = yes Eq.refl
... | false = no (λ ())

runtimeCandidateSystem :
  (kb : KnowledgeBase) →
  RuntimeClause →
  List String →
  PositiveConstraintSystem
Entity (runtimeCandidateSystem kb before rules) =
  RuntimeCandidate kb before
Constraint (runtimeCandidateSystem kb before rules) =
  RawContextConstraint
Bridge (runtimeCandidateSystem kb before rules) candidate =
  RuntimeAdmissible
    kb before
    (candidateAfter candidate)
    (candidateCertificate candidate)
Holds (runtimeCandidateSystem kb before rules) candidate constraint =
  ( singleConstraintCheck
      kb
      (RawCertificate.rawTarget (candidateCertificate candidate))
      constraint
    and any
      (stringEqual (rawConstraintProvenance constraint))
      rules
  )
    Eq.≡ true
decide (runtimeCandidateSystem kb before rules) =
  runtimeCandidateDecision kb before rules

runtimeCandidatePaths :
  (kb : KnowledgeBase) →
  (before : RuntimeClause) →
  (rules : List String) →
  PathSystem (runtimeCandidateSystem kb before rules)
Meaning (runtimeCandidatePaths kb before rules) =
  Completion (RuntimeSystem kb) clause clause
implicit (runtimeCandidatePaths kb before rules) =
  raw (translate before)
explicit (runtimeCandidatePaths kb before rules) candidate =
  raw (translate (candidateAfter candidate))
basePath (runtimeCandidatePaths kb before rules) candidate accepted =
  hardCellPath
    (checkedRewrite accepted)

runtimeContextualHomotopyTower :
  (kb : KnowledgeBase) →
  (before : RuntimeClause) →
  (rules : List String) →
  (compatibility :
    CompatibilitySystem (runtimeCandidateSystem kb before rules)) →
  ContextualHomotopyTower
    (runtimeCandidateSystem kb before rules)
    (runtimeCandidatePaths kb before rules)
    compatibility
runtimeContextualHomotopyTower kb before rules compatibility =
  contextualHomotopyTower
    (runtimeCandidateSystem kb before rules)
    (runtimeCandidatePaths kb before rules)
    compatibility
