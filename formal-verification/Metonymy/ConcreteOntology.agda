{-# OPTIONS --cubical #-}

module Metonymy.ConcreteOntology where

open import Cubical.Foundations.Prelude
open import Cubical.Data.Bool
open import Cubical.Data.Bool.Properties
open import Cubical.Data.Unit
open import Cubical.Data.Empty

open import Metonymy.Ontology
open import Metonymy.Compression
open import Metonymy.CompressionTheory
import Metonymy.Grammar as Grammar
import Metonymy.Cell as Cell

data Entity₀ : Type where
  author work book text other : Entity₀

data Edge₀ : Entity₀ → Entity₀ → Type where
  authorWork : Edge₀ author work
  authorBook : Edge₀ author book
  workText   : Edge₀ work text
  bookText   : Edge₀ book text
  authorOther : Edge₀ author other

Ontology₀ : OntologySignature
Entity Ontology₀ =
  Entity₀
Edge Ontology₀ =
  Edge₀

workRoute bookRoute : BridgePath Ontology₀ author text
workRoute =
  edge authorWork then edge workText
bookRoute =
  edge authorBook then edge bookText

pathCode :
  {x y : Entity₀} →
  BridgePath Ontology₀ x y →
  Bool
pathCode (identity x) =
  true
pathCode (edge authorWork) =
  true
pathCode (edge authorBook) =
  true
pathCode (edge workText) =
  true
pathCode (edge bookText) =
  true
pathCode (edge authorOther) =
  false
pathCode (compose left right) with pathCode left | pathCode right
... | true | true = true
... | _ | _ = false

BasicBridge₂₀ :
  {x y : Entity₀} →
  BridgePath Ontology₀ x y →
  BridgePath Ontology₀ x y →
  Type
BasicBridge₂₀ left right =
  pathCode left ≡ pathCode right

Coherence₀ : BridgeCoherence Ontology₀
Basic₂ Coherence₀ =
  BasicBridge₂₀

routeCoherence :
  Bridge₂ Coherence₀ workRoute bookRoute
routeCoherence =
  basic₂ refl

data Context₀ : Type where
  readingContext : Context₀

data Hole₀ : Type where
  readableObject : Hole₀

data Fits₀ : Context₀ → Hole₀ → Entity₀ → Type where
  workFits  : Fits₀ readingContext readableObject work
  bookFits  : Fits₀ readingContext readableObject book
  otherFits : Fits₀ readingContext readableObject other

Resolution₀ : ResolutionSignature Ontology₀
Context Resolution₀ =
  Context₀
Hole Resolution₀ =
  Hole₀
Fits Resolution₀ =
  Fits₀
HardLicense Resolution₀ Γ K path =
  Unit
PreferenceLicense Resolution₀ Γ K path =
  Unit
PromotionEvidence Resolution₀ Γ K path preferred =
  Unit
promoteLicense Resolution₀ Γ K path preferred evidence =
  tt

workResolution :
  HardResolution
    Resolution₀
    readingContext
    readableObject
    author
    work
workResolution =
  hardResolution
    (edge authorWork)
    workFits
    tt

bookResolution :
  HardResolution
    Resolution₀
    readingContext
    readableObject
    author
    book
bookResolution =
  hardResolution
    (edge authorBook)
    bookFits
    tt

otherResolution :
  HardResolution
    Resolution₀
    readingContext
    readableObject
    author
    other
otherResolution =
  hardResolution
    (edge authorOther)
    otherFits
    tt

classCode : Entity₀ → Bool
classCode work =
  true
classCode book =
  true
classCode _ =
  false

Compression₀ : CompressionSignature Ontology₀ Resolution₀
TargetCompatible Compression₀ Γ K left right =
  classCode left ≡ classCode right
targetCompatibleRefl Compression₀ fits =
  refl
targetCompatibleSym Compression₀ leftFits rightFits =
  sym
targetCompatibleTrans Compression₀
  firstFits secondFits thirdFits =
  _∙_

fineWork fineBook fineOther :
  Fine readingContext readableObject author
fineWork =
  fine work workResolution
fineBook =
  fine book bookResolution
fineOther =
  fine other otherResolution

workBookCompatible :
  SameMetonymicClass Compression₀ fineWork fineBook
workBookCompatible =
  refl

workBookPath :
  Path
    (Coarse Compression₀ readingContext readableObject author)
    (contract {C = Compression₀} fineWork)
    (contract {C = Compression₀} fineBook)
workBookPath =
  glue {C = Compression₀}
    fineWork fineBook workBookCompatible

classifier :
  CompressionModel
    Compression₀
    readingContext
    readableObject
    author
Meaning classifier =
  Bool
classify classifier explicitValue =
  classCode (target explicitValue)
respectCompatibility classifier left right compatible =
  compatible

workOtherDoNotCollapse :
  contract {C = Compression₀} fineWork
    ≢
  contract {C = Compression₀} fineOther
workOtherDoNotCollapse =
  separatedCompressedMeanings
    classifier
    fineWork
    fineOther
    true≢false

data Interface₁ : Type where
  clause₁ : Interface₁

data Rule₁ : Interface₁ → Interface₁ → Type where
  implicitAuthor₁ explicitText₁ :
    Rule₁ clause₁ clause₁

Grammar₁ : Grammar.GrammarSignature
Grammar.Interface Grammar₁ =
  Interface₁
Grammar.Rule Grammar₁ =
  Rule₁

implicitAuthorDerivation explicitTextDerivation :
  Grammar.RawDerivation Grammar₁ clause₁ clause₁
implicitAuthorDerivation =
  Grammar.rule implicitAuthor₁
explicitTextDerivation =
  Grammar.rule explicitText₁

record GroundHardCell
  {A B : Interface₁}
  (f g : Grammar.RawDerivation Grammar₁ A B) :
  Type where

  constructor groundHardCell
  field
    groundedPath :
      BridgePath Ontology₀ author text

open GroundHardCell public

throughWork throughBook :
  GroundHardCell
    implicitAuthorDerivation
    explicitTextDerivation
throughWork =
  groundHardCell workRoute
throughBook =
  groundHardCell bookRoute

data NoPreferredCell :
  {A B : Interface₁} →
  Grammar.RawDerivation Grammar₁ A B →
  Grammar.RawDerivation Grammar₁ A B →
  Type where

GroundBasic₂ :
  {A B : Interface₁} →
  {f g : Grammar.RawDerivation Grammar₁ A B} →
  GroundHardCell f g →
  GroundHardCell f g →
  Type
GroundBasic₂ left right =
  Bridge₂ Coherence₀
    (groundedPath left)
    (groundedPath right)

GroundSystem : Cell.MetonymicSystem Grammar₁
Cell.HardCell GroundSystem =
  GroundHardCell
Cell.PreferredCell GroundSystem =
  NoPreferredCell
Cell.PromotionEvidence GroundSystem preferred =
  ⊥
Cell.promote GroundSystem () evidence
Cell.Basic₂ GroundSystem =
  GroundBasic₂

ontologyGroundedCell₂ :
  Cell.Cell₂ GroundSystem throughWork throughBook
ontologyGroundedCell₂ =
  Cell.basic₂ routeCoherence
