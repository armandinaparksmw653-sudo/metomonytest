{-# OPTIONS --cubical #-}

module Metonymy.RuntimeModel where

open import Cubical.Foundations.Prelude
open import Cubical.Data.Bool
open import Cubical.Data.Unit
open import Agda.Builtin.List
open import Agda.Builtin.Maybe
import Agda.Builtin.Equality as Eq

open import Metonymy.Grammar
open import Metonymy.Cell
import Metonymy.Cell as Cell
open import Metonymy.Completion
open import Metonymy.Semantics
open import Metonymy.MetaTheory
open import Metonymy.Checker
open import Metonymy.EndToEnd
import Metonymy.Compression as Compression
import Metonymy.ConcreteOntology as CO
import Metonymy.RuntimeBridge as RuntimeBridge

data NP : Type where
  john rumi rumiWorks unrelatedNP : NP

data Verb : Type where
  read scrutinize : Verb

data VP : Type where
  compl : Verb → NP → VP

data GFTree : Type where
  pred : NP → VP → GFTree

data Interfaceᵣ : Type where
  clause : Interfaceᵣ

data Ruleᵣ : Interfaceᵣ → Interfaceᵣ → Type where
  parsedClause :
    GFTree →
    Ruleᵣ clause clause

Grammarᵣ : GrammarSignature
Interface Grammarᵣ =
  Interfaceᵣ
Rule Grammarᵣ =
  Ruleᵣ

translate :
  GFTree →
  RawDerivation Grammarᵣ clause clause
translate tree =
  rule (parsedClause tree)

implicitTree explicitTree unrelatedTree : GFTree
implicitTree =
  pred john (compl read rumi)
explicitTree =
  pred john (compl read rumiWorks)
unrelatedTree =
  pred john (compl read unrelatedNP)

implicitDerivation explicitDerivation unrelatedDerivation :
  RawDerivation Grammarᵣ clause clause
implicitDerivation =
  translate implicitTree
explicitDerivation =
  translate explicitTree
unrelatedDerivation =
  translate unrelatedTree

runtimeKB : KnowledgeBase
runtimeKB =
  knowledgeBase
    ( typeFact "Q43347" "Writer"
    ∷ typeFact "works-of-Q43347" "LiteraryWork"
    ∷ []
    )
    ( relationFact "Authored" "Q43347" "works-of-Q43347"
    ∷ []
    )
    ( subsortRule "Writer" "Human"
    ∷ subsortRule "LiteraryWork" "Readable"
    ∷ []
    )
    ( predicateFact
        "Read"
        (hasSort "Human")
        (hasSort "Readable")
        "HardRequirement"
        "local:selectional-lexicon"
    ∷ predicateFact
        "VN_Scrutinize"
        (hasSort "Human")
        (hasSort "Readable")
        "SelectionalPreference"
        "VerbNet:Scrutiny"
    ∷ []
    )
    ( lexemeFact "John" "john"
    ∷ lexemeFact "Author_Q43347" "Q43347"
    ∷ lexemeFact "Works_Q43347" "works-of-Q43347"
    ∷ lexemeFact "Unrelated" "unrelated"
    ∷ []
    )

hardCertificate : RawCertificate
hardCertificate =
  rawCertificate
    expand
    defaultForgetContext
    "Read"
    objectHole
    "Q43347"
    "works-of-Q43347"
    (hasSort "Readable")
    "HardRequirement"
    "local:selectional-lexicon"
    (edge "Authored" "Q43347" "works-of-Q43347" ∷ [])

preferenceCertificate : RawCertificate
preferenceCertificate =
  rawCertificate
    expand
    defaultForgetContext
    "VN_Scrutinize"
    objectHole
    "Q43347"
    "works-of-Q43347"
    (hasSort "Readable")
    "SelectionalPreference"
    "VerbNet:Scrutiny"
    (edge "Authored" "Q43347" "works-of-Q43347" ∷ [])

quantifiedForgetContext : ForgetContext
quantifiedForgetContext =
  forgetContext true false true true true false false

unsafeContractCertificate : RawCertificate
unsafeContractCertificate =
  rawCertificate
    contract
    quantifiedForgetContext
    "Read"
    objectHole
    "Q43347"
    "works-of-Q43347"
    (hasSort "Readable")
    "HardRequirement"
    "local:selectional-lexicon"
    (edge "Authored" "Q43347" "works-of-Q43347" ∷ [])

unsafeContractBefore unsafeContractAfter : RuntimeClause
unsafeContractBefore =
  runtimeClause
    "John"
    "Read"
    "Works_Q43347"
    quantifiedForgetContext
unsafeContractAfter =
  runtimeClause
    "John"
    "Read"
    "Author_Q43347"
    quantifiedForgetContext

quantifiedContractionRejected :
  runtimeCheck
    runtimeKB
    unsafeContractBefore
    unsafeContractAfter
    unsafeContractCertificate
    Eq.≡
    false
quantifiedContractionRejected =
  Eq.refl

hardCheck :
  check runtimeKB hardCertificate Eq.≡ true
hardCheck =
  Eq.refl

structuredRequirementAccepted :
  satisfiesRequirement
    runtimeKB
    "works-of-Q43347"
    ( allOf
        ( anyOf (hasSort "Audible" ∷ hasSort "Readable" ∷ [])
        ∷ notRequirement (hasSort "Human")
        ∷ []
        )
    )
    Eq.≡
    true
structuredRequirementAccepted =
  Eq.refl

hardStrength :
  isHardRequirement hardCertificate Eq.≡ true
hardStrength =
  Eq.refl

preferenceCheck :
  check runtimeKB preferenceCertificate Eq.≡ true
preferenceCheck =
  Eq.refl

preferenceStrength :
  isSelectionalPreference preferenceCertificate Eq.≡ true
preferenceStrength =
  Eq.refl

data PreferredCellᵣ :
  {A B : Interfaceᵣ} →
  RawDerivation Grammarᵣ A B →
  RawDerivation Grammarᵣ A B →
  Type where

  scrutinizeRumiWorksᵣ :
    AcceptedCertificate
      runtimeKB
      preferenceCertificate
      isSelectionalPreference →
    PreferredCellᵣ
      (translate (pred john (compl scrutinize rumi)))
      (translate (pred john (compl scrutinize rumiWorks)))

preferenceEvidence : RawDiscourseEvidence
preferenceEvidence =
  targetSalient
    "works-of-Q43347"
    "conversation:turn-4"

preferencePromotionCheck :
  checkPromotion
    preferenceCertificate
    (just preferenceEvidence)
    Eq.≡
    true
preferencePromotionCheck =
  Eq.refl

runtimePromotionEvidence :
  ValidatedDiscourseEvidence
    preferenceCertificate
    preferenceEvidence
runtimePromotionEvidence =
  promotionSound
    preferenceCertificate
    preferenceEvidence
    preferencePromotionCheck

PromotionEvidenceFor :
  {A B : Interfaceᵣ} →
  {f g : RawDerivation Grammarᵣ A B} →
  PreferredCellᵣ f g →
  Type
PromotionEvidenceFor (scrutinizeRumiWorksᵣ accepted) =
  ValidatedDiscourseEvidence
    preferenceCertificate
    preferenceEvidence

data HardCellᵣ :
  {A B : Interfaceᵣ} →
  RawDerivation Grammarᵣ A B →
  RawDerivation Grammarᵣ A B →
  Type where

  hardIdentityᵣ :
    {A B : Interfaceᵣ} →
    (derivation : RawDerivation Grammarᵣ A B) →
    HardCellᵣ derivation derivation

  hardRumiWorksᵣ :
    AcceptedCertificate
      runtimeKB
      hardCertificate
      isHardRequirement →
    HardCellᵣ implicitDerivation explicitDerivation

  hardPromotedᵣ :
    {A B : Interfaceᵣ} →
    {left right : RawDerivation Grammarᵣ A B} →
    (preferred : PreferredCellᵣ left right) →
    PromotionEvidenceFor preferred →
    HardCellᵣ left right

  hardComposeᵣ :
    {A B : Interfaceᵣ} →
    {C : Interfaceᵣ} →
    {left left' : RawDerivation Grammarᵣ A B} →
    {right right' : RawDerivation Grammarᵣ B C} →
    HardCellᵣ left left' →
    HardCellᵣ right right' →
    HardCellᵣ (left then right) (left' then right')

data Basic₂ᵣ
  {A B : Interfaceᵣ}
  {f g : RawDerivation Grammarᵣ A B} :
  HardCellᵣ f g →
  HardCellᵣ f g →
  Type where

  sameHardCellᵣ :
    {cell : HardCellᵣ f g} →
    Basic₂ᵣ cell cell

Systemᵣ : MetonymicSystem Grammarᵣ
HardCell Systemᵣ =
  HardCellᵣ
PreferredCell Systemᵣ =
  PreferredCellᵣ
PromotionEvidence Systemᵣ =
  PromotionEvidenceFor
promote Systemᵣ preferred evidence =
  hardPromotedᵣ preferred evidence
Basic₂ Systemᵣ =
  Basic₂ᵣ

runtimeAcceptedHard :
  AcceptedCertificate
    runtimeKB
    hardCertificate
    isHardRequirement
runtimeAcceptedHard =
  acceptCertificate
    runtimeKB
    hardCertificate
    isHardRequirement
    hardCheck
    hardStrength

certificateToCell :
  AcceptedCertificate
    runtimeKB
    hardCertificate
    isHardRequirement →
  HardCell Systemᵣ implicitDerivation explicitDerivation
certificateToCell =
  hardRumiWorksᵣ

runtimeHardCell :
  HardCell Systemᵣ implicitDerivation explicitDerivation
runtimeHardCell =
  certificateToCell runtimeAcceptedHard

runtimeHardPath :
  Path
    (Completion Systemᵣ clause clause)
    (raw implicitDerivation)
    (raw explicitDerivation)
runtimeHardPath =
  hardCellPath runtimeHardCell

runtimeBeforeClause runtimeAfterClause :
  RuntimeClause
runtimeBeforeClause =
  runtimeClause
    "John"
    "Read"
    "Author_Q43347"
    defaultForgetContext
runtimeAfterClause =
  runtimeClause
    "John"
    "Read"
    "Works_Q43347"
    defaultForgetContext

runtimeRewriteCheck :
  runtimeCheck
    runtimeKB
    runtimeBeforeClause
    runtimeAfterClause
    hardCertificate
    Eq.≡
    true
runtimeRewriteCheck =
  Eq.refl

runtimeGFPath :
  Path
    ( Completion
        (RuntimeBridge.RuntimeSystem runtimeKB)
        RuntimeBridge.clause
        RuntimeBridge.clause
    )
    ( raw
        (RuntimeBridge.translate runtimeBeforeClause)
    )
    ( raw
        (RuntimeBridge.translate runtimeAfterClause)
    )
runtimeGFPath =
  RuntimeBridge.checkedRuntimePath
    runtimeKB
    runtimeBeforeClause
    runtimeAfterClause
    hardCertificate
    runtimeRewriteCheck

runtimeGenericSemanticEquality :
  Path
    (RuntimeBridge.RuntimeMeaning runtimeKB)
    ( interpret
        (RuntimeBridge.runtimeSemantics runtimeKB)
        (raw (RuntimeBridge.translate runtimeBeforeClause))
    )
    ( interpret
        (RuntimeBridge.runtimeSemantics runtimeKB)
        (raw (RuntimeBridge.translate runtimeAfterClause))
    )
runtimeGenericSemanticEquality =
  RuntimeBridge.checkedRuntimeSemanticEquality
    runtimeKB
    runtimeBeforeClause
    runtimeAfterClause
    hardCertificate
    runtimeRewriteCheck

runtimeAcceptedPreference :
  AcceptedCertificate
    runtimeKB
    preferenceCertificate
    isSelectionalPreference
runtimeAcceptedPreference =
  acceptCertificate
    runtimeKB
    preferenceCertificate
    isSelectionalPreference
    preferenceCheck
    preferenceStrength

runtimePreference :
  PreferredCell
    Systemᵣ
    (translate (pred john (compl scrutinize rumi)))
    (translate (pred john (compl scrutinize rumiWorks)))
runtimePreference =
  scrutinizeRumiWorksᵣ runtimeAcceptedPreference

runtimePromotedPath :
  Path
    (Completion Systemᵣ clause clause)
    (raw (translate (pred john (compl scrutinize rumi))))
    (raw (translate (pred john (compl scrutinize rumiWorks))))
runtimePromotedPath =
  promoteAcceptedPreference
    runtimePreference
    runtimePromotionEvidence

CompressedMeaning : Type
CompressedMeaning =
  Compression.Coarse
    CO.Compression₀
    CO.readingContext
    CO.readableObject
    CO.author

compressedTreeMeaning :
  GFTree →
  CompressedMeaning
compressedTreeMeaning (pred john (compl read rumi)) =
  Compression.contract {C = CO.Compression₀} CO.fineWork
compressedTreeMeaning (pred john (compl read rumiWorks)) =
  Compression.contract {C = CO.Compression₀} CO.fineBook
compressedTreeMeaning (pred john (compl scrutinize rumi)) =
  Compression.contract {C = CO.Compression₀} CO.fineWork
compressedTreeMeaning (pred john (compl scrutinize rumiWorks)) =
  Compression.contract {C = CO.Compression₀} CO.fineBook
compressedTreeMeaning _ =
  Compression.contract {C = CO.Compression₀} CO.fineOther

compressedRawMeaning :
  {A B : Interfaceᵣ} →
  RawDerivation Grammarᵣ A B →
  CompressedMeaning
compressedRawMeaning identity =
  Compression.contract {C = CO.Compression₀} CO.fineOther
compressedRawMeaning (rule (parsedClause tree)) =
  compressedTreeMeaning tree
compressedRawMeaning (compose left right) =
  Compression.contract {C = CO.Compression₀} CO.fineOther

compressedRespectCell :
  {A B : Interfaceᵣ} →
  {f g : RawDerivation Grammarᵣ A B} →
  HardCellᵣ f g →
  compressedRawMeaning f ≡ compressedRawMeaning g
compressedRespectCell (hardIdentityᵣ derivation) =
  refl
compressedRespectCell (hardRumiWorksᵣ accepted) =
  CO.workBookPath
compressedRespectCell
  (hardPromotedᵣ (scrutinizeRumiWorksᵣ accepted) evidence) =
  CO.workBookPath
compressedRespectCell (hardComposeᵣ left right) =
  refl

compressedRespectCoherence :
  {A B : Interfaceᵣ} →
  {f g : RawDerivation Grammarᵣ A B} →
  {left right : HardCellᵣ f g} →
  (square : Cell₂ Systemᵣ left right) →
  compressedRespectCell left ≡ compressedRespectCell right
compressedRespectCoherence Cell.refl₂ =
  refl
compressedRespectCoherence (Cell.basic₂ sameHardCellᵣ) =
  refl
compressedRespectCoherence (Cell.sym₂ square) =
  sym (compressedRespectCoherence square)
compressedRespectCoherence (Cell.trans₂ first second) =
  compressedRespectCoherence first
    ∙ compressedRespectCoherence second

runtimeSemantics :
  SemanticModel Systemᵣ clause clause
Meaning runtimeSemantics =
  CompressedMeaning
interpretRaw runtimeSemantics =
  compressedRawMeaning
respectCell runtimeSemantics =
  compressedRespectCell
respectCoherence runtimeSemantics =
  compressedRespectCoherence

runtimeSemanticEquality :
  Path
    CompressedMeaning
    (interpret runtimeSemantics (raw implicitDerivation))
    (interpret runtimeSemantics (raw explicitDerivation))
runtimeSemanticEquality =
  cong
    (interpret runtimeSemantics)
    runtimeHardPath

runtimeNonCollapse :
  raw implicitDerivation
    ≢
  raw unrelatedDerivation
runtimeNonCollapse =
  separatedBySemantics
    runtimeSemantics
    implicitDerivation
    unrelatedDerivation
    CO.workOtherDoNotCollapse
