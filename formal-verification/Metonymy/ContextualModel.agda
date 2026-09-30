{-# OPTIONS --cubical #-}

module Metonymy.ContextualModel where

open import Cubical.Foundations.Prelude
open import Agda.Builtin.Bool
open import Agda.Builtin.List
import Agda.Builtin.Equality as Eq

open import Metonymy.Checker
open import Metonymy.RuntimeBridge
open import Metonymy.Completion

waterlooKB : KnowledgeBase
waterlooKB =
  knowledgeBase
    ( typeFact "Q1049470" "Organization"
    ∷ typeFact "Q7974219" "Organization"
    ∷ []
    )
    ( relationFact "InstitutionOf" "Q639408" "Q1049470"
    ∷ relationFact "InstitutionOf" "Q639408" "Q7974219"
    ∷ relationFact "Conducts" "Q1049470" "Q413"
    ∷ []
    )
    []
    ( predicateFact
        "AnnounceGF"
        (anyOf (hasSort "Animate" ∷ hasSort "Organization" ∷ []))
        (hasSort "Entity")
        "HardRequirement"
        "contextual-rules-1"
    ∷ []
    )
    ( lexemeFact "WaterlooGF" "Q639408"
    ∷ lexemeFact "UniversityGF" "Q1049470"
    ∷ lexemeFact "CouncilGF" "Q7974219"
    ∷ lexemeFact "ProgrammeGF" "Q413"
    ∷ []
    )

beforeClause afterClause : RuntimeClause
beforeClause =
  runtimeClause "WaterlooGF" "AnnounceGF" "ProgrammeGF"
    defaultForgetContext
afterClause =
  runtimeClause "UniversityGF" "AnnounceGF" "ProgrammeGF"
    defaultForgetContext

waterlooCertificate : RawCertificate
waterlooCertificate =
  rawCertificate
    expand
    defaultForgetContext
    "AnnounceGF"
    subjectHole
    "Q639408"
    "Q1049470"
    (anyOf (hasSort "Animate" ∷ hasSort "Organization" ∷ []))
    "HardRequirement"
    "contextual-rules-1"
    (edge "InstitutionOf" "Q639408" "Q1049470" ∷ [])

announceAnchor physicsAnchor : RawLexicalAnchor
announceAnchor =
  rawLexicalAnchor "Verb" "announce" "announced" 9 18
physicsAnchor =
  rawLexicalAnchor "Noun" "physics" "physics" 38 45

announceConstraint physicsConstraint : RawContextConstraint
announceConstraint =
  rawContextConstraint
    announceAnchor
    (rawRequires
      (anyOf (hasSort "Animate" ∷ hasSort "Organization" ∷ [])))
    "VerbNet:say-37.7"
physicsConstraint =
  rawContextConstraint
    physicsAnchor
    (rawRequiresRelation "Conducts" "Q413")
    "context-template:programme-in-topic:v1"

Γ₀ Γ₁ Γ₂ : RawContext
Γ₀ = rawContext "waterloo-snapshot-v1" "announce" [] []
Γ₁ = rawContext "waterloo-snapshot-v1" "announce"
  (announceConstraint ∷ [])
  ("VerbNet:say-37.7" ∷ [])
Γ₂ = rawContext "waterloo-snapshot-v1" "announce"
  (announceConstraint ∷ physicsConstraint ∷ [])
  ( "VerbNet:say-37.7"
  ∷ "context-template:programme-in-topic:v1"
  ∷ []
  )

stage₀Checked :
  contextualRuntimeCheck
    waterlooKB beforeClause afterClause waterlooCertificate
    "waterloo-snapshot-v1" Γ₀
    Eq.≡ true
stage₀Checked = Eq.refl

stage₁Checked :
  contextualRuntimeCheck
    waterlooKB beforeClause afterClause waterlooCertificate
    "waterloo-snapshot-v1" Γ₁
    Eq.≡ true
stage₁Checked = Eq.refl

stage₂Checked :
  contextualRuntimeCheck
    waterlooKB beforeClause afterClause waterlooCertificate
    "waterloo-snapshot-v1" Γ₂
    Eq.≡ true
stage₂Checked = Eq.refl

waterlooStage₀Path :
  Path
    (Completion (RuntimeSystem waterlooKB) clause clause)
    (raw (translate beforeClause))
    (raw (translate afterClause))
waterlooStage₀Path =
  checkedContextualRuntimePath
    waterlooKB beforeClause afterClause waterlooCertificate
    "waterloo-snapshot-v1" Γ₀ stage₀Checked

waterlooStage₁Path :
  Path
    (Completion (RuntimeSystem waterlooKB) clause clause)
    (raw (translate beforeClause))
    (raw (translate afterClause))
waterlooStage₁Path =
  checkedContextualRuntimePath
    waterlooKB beforeClause afterClause waterlooCertificate
    "waterloo-snapshot-v1" Γ₁ stage₁Checked

waterlooStage₂Path :
  Path
    (Completion (RuntimeSystem waterlooKB) clause clause)
    (raw (translate beforeClause))
    (raw (translate afterClause))
waterlooStage₂Path =
  checkedContextualRuntimePath
    waterlooKB beforeClause afterClause waterlooCertificate
    "waterloo-snapshot-v1" Γ₂ stage₂Checked

councilPhysicsObstruction :
  rawConstraintHolds waterlooKB "Q7974219" physicsConstraint Eq.≡ false
councilPhysicsObstruction = Eq.refl

waterlooStagePathStability₀₁ :
  waterlooStage₀Path ≡ waterlooStage₁Path
waterlooStagePathStability₀₁ = refl

waterlooStagePathStability₁₂ :
  waterlooStage₁Path ≡ waterlooStage₂Path
waterlooStagePathStability₁₂ = refl
