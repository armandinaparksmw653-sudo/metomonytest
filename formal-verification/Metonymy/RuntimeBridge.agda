{-# OPTIONS --cubical #-}

module Metonymy.RuntimeBridge where

open import Cubical.Foundations.Prelude
open import Cubical.Data.Empty
open import Cubical.Data.Sigma
open import Cubical.Data.List.Base
  using (List; []; _∷_; _++_)
open import Cubical.HITs.TypeQuotients.Base
open import Agda.Builtin.Bool
open import Agda.Builtin.String
import Agda.Builtin.Equality as Eq

open import Metonymy.Grammar
open import Metonymy.Cell
import Metonymy.Cell as Cell
open import Metonymy.Completion
open import Metonymy.Semantics
open import Metonymy.Checker
open import Metonymy.EndToEnd

data RuntimeInterface : Type where
  clause : RuntimeInterface

data RuntimeRule : RuntimeInterface → RuntimeInterface → Type where
  parsedClause :
    RuntimeClause →
    RuntimeRule clause clause

RuntimeGrammar : GrammarSignature
Interface RuntimeGrammar =
  RuntimeInterface
Rule RuntimeGrammar =
  RuntimeRule

translate :
  RuntimeClause →
  RawDerivation RuntimeGrammar clause clause
translate tree =
  rule (parsedClause tree)

data RuntimeHardCell
  (kb : KnowledgeBase) :
  {A B : RuntimeInterface} →
  RawDerivation RuntimeGrammar A B →
  RawDerivation RuntimeGrammar A B →
  Type where

  checkedRewrite :
    {before after : RuntimeClause} →
    {certificate : RawCertificate} →
    RuntimeAdmissible kb before after certificate →
    RuntimeHardCell kb
      (translate before)
      (translate after)

data NoPreferredCell :
  {A B : RuntimeInterface} →
  RawDerivation RuntimeGrammar A B →
  RawDerivation RuntimeGrammar A B →
  Type where

data RuntimeBasic₂
  {kb : KnowledgeBase}
  {A B : RuntimeInterface}
  {f g : RawDerivation RuntimeGrammar A B} :
  RuntimeHardCell kb f g →
  RuntimeHardCell kb f g →
  Type where

  sameCheckedRewrite :
    {cell : RuntimeHardCell kb f g} →
    RuntimeBasic₂ cell cell

RuntimeSystem :
  KnowledgeBase →
  MetonymicSystem RuntimeGrammar
HardCell (RuntimeSystem kb) =
  RuntimeHardCell kb
PreferredCell (RuntimeSystem kb) =
  NoPreferredCell
PromotionEvidence (RuntimeSystem kb) preferred =
  ⊥
promote (RuntimeSystem kb) () evidence
Basic₂ (RuntimeSystem kb) =
  RuntimeBasic₂

certificateToRuntimeCell :
  (kb : KnowledgeBase) →
  (before after : RuntimeClause) →
  (certificate : RawCertificate) →
  runtimeCheck kb before after certificate Eq.≡ true →
  HardCell
    (RuntimeSystem kb)
    (translate before)
    (translate after)
certificateToRuntimeCell kb before after certificate checked =
  checkedRewrite
    (runtimeCheckSound kb before after certificate checked)

checkedRuntimePath :
  (kb : KnowledgeBase) →
  (before after : RuntimeClause) →
  (certificate : RawCertificate) →
  runtimeCheck kb before after certificate Eq.≡ true →
  Path
    (Completion (RuntimeSystem kb) clause clause)
    (raw (translate before))
    (raw (translate after))
checkedRuntimePath kb before after certificate checked =
  hardCellPath
    ( certificateToRuntimeCell
        kb before after certificate checked
    )

checkedContextualRuntimePath :
  (kb : KnowledgeBase) →
  (before after : RuntimeClause) →
  (certificate : RawCertificate) →
  (snapshotHash : String) →
  (context : RawContext) →
  contextualRuntimeCheck
    kb before after certificate snapshotHash context
    Eq.≡ true →
  Path
    (Completion (RuntimeSystem kb) clause clause)
    (raw (translate before))
    (raw (translate after))
checkedContextualRuntimePath
  kb before after certificate snapshotHash context checked =
  checkedRuntimePath
    kb before after certificate
    ( ContextualRuntimeAdmissible.contextualRuntimeProof
      ( contextualRuntimeCheckSound
        kb before after certificate snapshotHash context checked
      )
    )

RuntimeRelated :
  KnowledgeBase →
  RuntimeClause →
  RuntimeClause →
  Type
RuntimeRelated kb before after =
  Σ[ certificate ∈ RawCertificate ]
    RuntimeAdmissible kb before after certificate

RuntimeClauseClass :
  KnowledgeBase →
  Type
RuntimeClauseClass kb =
  RuntimeClause /ₜ RuntimeRelated kb

RuntimeMeaning :
  KnowledgeBase →
  Type
RuntimeMeaning kb =
  List (RuntimeClauseClass kb)

runtimeRawMeaning :
  {kb : KnowledgeBase} →
  {A B : RuntimeInterface} →
  RawDerivation RuntimeGrammar A B →
  RuntimeMeaning kb
runtimeRawMeaning identity =
  []
runtimeRawMeaning (rule (parsedClause tree)) =
  [ tree ] ∷ []
runtimeRawMeaning (compose left right) =
  runtimeRawMeaning left ++ runtimeRawMeaning right

runtimeRespectCell :
  {kb : KnowledgeBase} →
  {A B : RuntimeInterface} →
  {f g : RawDerivation RuntimeGrammar A B} →
  RuntimeHardCell kb f g →
  runtimeRawMeaning {kb = kb} f
    ≡
  runtimeRawMeaning {kb = kb} g
runtimeRespectCell
  ( checkedRewrite
      {before = before}
      {after = after}
      {certificate = certificate}
      admitted
  ) =
  cong
    (λ atom → atom ∷ [])
    (eq/ before after (certificate , admitted))

runtimeRespectCoherence :
  {kb : KnowledgeBase} →
  {A B : RuntimeInterface} →
  {f g : RawDerivation RuntimeGrammar A B} →
  {left right : RuntimeHardCell kb f g} →
  (square : Cell₂ (RuntimeSystem kb) left right) →
  runtimeRespectCell left ≡ runtimeRespectCell right
runtimeRespectCoherence Cell.refl₂ =
  refl
runtimeRespectCoherence
  (Cell.basic₂ sameCheckedRewrite) =
  refl
runtimeRespectCoherence (Cell.sym₂ square) =
  sym (runtimeRespectCoherence square)
runtimeRespectCoherence (Cell.trans₂ first second) =
  runtimeRespectCoherence first
    ∙ runtimeRespectCoherence second

runtimeSemantics :
  (kb : KnowledgeBase) →
  SemanticModel
    (RuntimeSystem kb)
    clause
    clause
Meaning (runtimeSemantics kb) =
  RuntimeMeaning kb
interpretRaw (runtimeSemantics kb) =
  runtimeRawMeaning
respectCell (runtimeSemantics kb) =
  runtimeRespectCell
respectCoherence (runtimeSemantics kb) =
  runtimeRespectCoherence

checkedRuntimeSemanticEquality :
  (kb : KnowledgeBase) →
  (before after : RuntimeClause) →
  (certificate : RawCertificate) →
  runtimeCheck kb before after certificate Eq.≡ true →
  Path
    (RuntimeMeaning kb)
    ( interpret
        (runtimeSemantics kb)
        (raw (translate before))
    )
    ( interpret
        (runtimeSemantics kb)
        (raw (translate after))
    )
checkedRuntimeSemanticEquality
  kb before after certificate checked =
  cong
    (interpret (runtimeSemantics kb))
    ( checkedRuntimePath
        kb before after certificate checked
    )
