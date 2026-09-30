{-# OPTIONS --cubical #-}

module Metonymy.EndToEnd where

open import Cubical.Foundations.Prelude
open import Agda.Builtin.Bool
import Agda.Builtin.Equality as Eq
open import Metonymy.Checker
open import Metonymy.Grammar
open import Metonymy.Cell
open import Metonymy.Completion

hardCellPath :
  {G : GrammarSignature} →
  {M : MetonymicSystem G} →
  {A B : Interface G} →
  {f g : RawDerivation G A B} →
  HardCell M f g →
  Path
    (Completion M A B)
    (raw f)
    (raw g)
hardCellPath =
  metonymic

acceptedPreference :
  {G : GrammarSignature} →
  {M : MetonymicSystem G} →
  {A B : Interface G} →
  {f g : RawDerivation G A B} →
  (kb : KnowledgeBase) →
  (certificate : RawCertificate) →
  check kb certificate Eq.≡ true →
  isSelectionalPreference certificate Eq.≡ true →
  ( Admissible kb certificate →
    isSelectionalPreference certificate Eq.≡ true →
    PreferredCell M f g
  ) →
  PreferredCell M f g
acceptedPreference kb certificate checked preferred realize =
  realize (checkSound kb certificate checked) preferred

promoteAcceptedPreference :
  {G : GrammarSignature} →
  {M : MetonymicSystem G} →
  {A B : Interface G} →
  {f g : RawDerivation G A B} →
  (preferred : PreferredCell M f g) →
  PromotionEvidence M preferred →
  Path
    (Completion M A B)
    (raw f)
    (raw g)
promoteAcceptedPreference preferred evidence =
  promotedPath preferred evidence
