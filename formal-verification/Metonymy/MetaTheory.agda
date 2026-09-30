{-# OPTIONS --cubical #-}

module Metonymy.MetaTheory where

open import Cubical.Foundations.Prelude
open import Cubical.Foundations.Equiv
open import Cubical.Foundations.Isomorphism
open import Cubical.Data.Empty as Empty
open import Metonymy.Grammar
open import Metonymy.Cell
open import Metonymy.Completion
open import Metonymy.Semantics

infix 3 _≢_

_≢_ : {A : Type} → A → A → Type
left ≢ right =
  left ≡ right → ⊥

NoHardCells :
  {G : GrammarSignature} →
  (M : MetonymicSystem G) →
  Type
NoHardCells {G} M =
  {A B : Interface G} →
  {f g : RawDerivation G A B} →
  HardCell M f g →
  ⊥

record CellErasure
  {G : GrammarSignature}
  (M : MetonymicSystem G) : Type₁ where

  field
    eraseCell :
      {A B : Interface G} →
      {f g : RawDerivation G A B} →
      HardCell M f g →
      f ≡ g

    eraseCoherence :
      {A B : Interface G} →
      {f g : RawDerivation G A B} →
      {left right : HardCell M f g} →
      (square : Cell₂ M left right) →
      eraseCell left ≡ eraseCell right

open CellErasure public

noCellsErasure :
  {G : GrammarSignature} →
  {M : MetonymicSystem G} →
  NoHardCells M →
  CellErasure M
eraseCell (noCellsErasure noCells) cell =
  Empty.rec (noCells cell)
eraseCoherence (noCellsErasure noCells) {left = left} square =
  Empty.rec (noCells left)

decodeWithErasure :
  {G : GrammarSignature} →
  {M : MetonymicSystem G} →
  CellErasure M →
  {A B : Interface G} →
  Completion M A B →
  RawDerivation G A B
decodeWithErasure erasure (raw derivation) =
  derivation
decodeWithErasure erasure (metonymic cell i) =
  eraseCell erasure cell i
decodeWithErasure erasure (coherent square i j) =
  eraseCoherence erasure square i j

decodeWithoutCells :
  {G : GrammarSignature} →
  {M : MetonymicSystem G} →
  NoHardCells M →
  {A B : Interface G} →
  Completion M A B →
  RawDerivation G A B
decodeWithoutCells noCells =
  decodeWithErasure (noCellsErasure noCells)

decodeRaw :
  {G : GrammarSignature} →
  {M : MetonymicSystem G} →
  (noCells : NoHardCells M) →
  {A B : Interface G} →
  (derivation : RawDerivation G A B) →
  decodeWithoutCells {M = M} noCells {A = A} {B = B}
    (raw derivation) ≡ derivation
decodeRaw {M = M} noCells {A = A} {B = B} derivation =
  refl

cellRetractionSquare :
  {G : GrammarSignature} →
  {M : MetonymicSystem G} →
  (noCells : NoHardCells M) →
  {A B : Interface G} →
  {f g : RawDerivation G A B} →
  (cell : HardCell M f g) →
  PathP
    ( λ i →
      raw {M = M}
        ( eraseCell
            (noCellsErasure {M = M} noCells)
            cell i
        )
        ≡
      metonymic {M = M} cell i
    )
    refl
    refl
cellRetractionSquare {M = M} noCells cell =
  Empty.rec (noCells cell)

coherenceRetractionCube :
  {G : GrammarSignature} →
  {M : MetonymicSystem G} →
  (noCells : NoHardCells M) →
  {A B : Interface G} →
  {f g : RawDerivation G A B} →
  {left right : HardCell M f g} →
  (square : Cell₂ M left right) →
  PathP
    ( λ i →
      PathP
        ( λ j →
          raw {M = M}
            ( eraseCoherence
                (noCellsErasure {M = M} noCells)
                square i j
            )
            ≡
          coherent {M = M} square i j
        )
        refl
        refl
    )
    (cellRetractionSquare {M = M} noCells left)
    (cellRetractionSquare {M = M} noCells right)
coherenceRetractionCube {M = M} noCells {left = left} square =
  Empty.rec (noCells left)

completionRetract :
  {G : GrammarSignature} →
  {M : MetonymicSystem G} →
  (noCells : NoHardCells M) →
  {A B : Interface G} →
  (completed : Completion M A B) →
  raw {M = M}
    (decodeWithoutCells {M = M} noCells completed)
    ≡ completed
completionRetract {M = M} noCells (raw derivation) =
  refl
completionRetract {M = M} noCells (metonymic cell i) =
  cellRetractionSquare {M = M} noCells cell i
completionRetract {M = M} noCells
  (coherent {left = left} square i j) =
  coherenceRetractionCube {M = M} noCells square i j

rawCompletionEquiv :
  {G : GrammarSignature} →
  {M : MetonymicSystem G} →
  (noCells : NoHardCells M) →
  {A B : Interface G} →
  RawDerivation G A B ≃ Completion M A B
rawCompletionEquiv {M = M} noCells {A = A} {B = B} =
  isoToEquiv
    ( iso
        raw
        (decodeWithoutCells {M = M} noCells {A = A} {B = B})
        (completionRetract {M = M} noCells {A = A} {B = B})
        (decodeRaw {M = M} noCells {A = A} {B = B})
    )

conservativity :
  {G : GrammarSignature} →
  {M : MetonymicSystem G} →
  (noCells : NoHardCells M) →
  {A B : Interface G} →
  {f g : RawDerivation G A B} →
  raw f ≡ raw g →
  f ≡ g
conservativity {M = M} noCells {A = A} {B = B} completedPath =
  cong
    (decodeWithoutCells {M = M} noCells {A = A} {B = B})
    completedPath

separatedBySemantics :
  {G : GrammarSignature} →
  {M : MetonymicSystem G} →
  {A B : Interface G} →
  (S : SemanticModel M A B) →
  (f g : RawDerivation G A B) →
  interpretRaw S f ≢ interpretRaw S g →
  raw f ≢ raw g
separatedBySemantics S f g meaningsDiffer completedPath =
  meaningsDiffer (cong (interpret S) completedPath)
