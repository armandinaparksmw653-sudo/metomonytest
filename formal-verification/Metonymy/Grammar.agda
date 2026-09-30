{-# OPTIONS --safe --without-K --cubical-compatible #-}

module Metonymy.Grammar where

record GrammarSignature : Set₁ where
  field
    Interface : Set
    Rule      : Interface → Interface → Set

open GrammarSignature public

data RawDerivation
  (G : GrammarSignature) :
  Interface G →
  Interface G →
  Set where

  identity :
    {A : Interface G} →
    RawDerivation G A A

  rule :
    {A B : Interface G} →
    Rule G A B →
    RawDerivation G A B

  compose :
    {A B C : Interface G} →
    RawDerivation G A B →
    RawDerivation G B C →
    RawDerivation G A C

infixl 7 _then_

_then_ :
  {G : GrammarSignature} →
  {A B C : Interface G} →
  RawDerivation G A B →
  RawDerivation G B C →
  RawDerivation G A C
_then_ = compose

data Structural₂
  {G : GrammarSignature} :
  {A B : Interface G} →
  RawDerivation G A B →
  RawDerivation G A B →
  Set where

  refl₂ :
    {A B : Interface G} →
    {f : RawDerivation G A B} →
    Structural₂ f f

  sym₂ :
    {A B : Interface G} →
    {f g : RawDerivation G A B} →
    Structural₂ f g →
    Structural₂ g f

  trans₂ :
    {A B : Interface G} →
    {f g h : RawDerivation G A B} →
    Structural₂ f g →
    Structural₂ g h →
    Structural₂ f h

  compose₂ :
    {A B C : Interface G} →
    {f f' : RawDerivation G A B} →
    {g g' : RawDerivation G B C} →
    Structural₂ f f' →
    Structural₂ g g' →
    Structural₂ (f then g) (f' then g')

  leftUnit₂ :
    {A B : Interface G} →
    (f : RawDerivation G A B) →
    Structural₂ (identity then f) f

  rightUnit₂ :
    {A B : Interface G} →
    (f : RawDerivation G A B) →
    Structural₂ (f then identity) f

  associate₂ :
    {A B C D : Interface G} →
    (f : RawDerivation G A B) →
    (g : RawDerivation G B C) →
    (h : RawDerivation G C D) →
    Structural₂
      ((f then g) then h)
      (f then (g then h))
