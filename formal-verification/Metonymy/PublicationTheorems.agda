{-# OPTIONS --cubical #-}

module Metonymy.PublicationTheorems where

-- Raw type-theoretical grammar and structural 2-cells.
import Metonymy.Grammar

-- Directed ontology paths, coherence, and hard/preferred resolutions.
import Metonymy.Ontology

-- Parallel grammatical cells and their 2-dimensional coherence.
import Metonymy.Cell

-- The freely generated 2-dimensional homotopical completion.
import Metonymy.Completion

-- Context-indexed compression using a witnessed compatibility relation.
import Metonymy.Compression

-- Independent semantics and its factorization through the completion.
import Metonymy.Semantics

-- Compression factorization, separation, and unique round-trip.
import Metonymy.CompressionTheory

-- Conservativity in the absence of cells and semantic non-collapse.
import Metonymy.MetaTheory

-- Executable checker with soundness and completeness reflection.
import Metonymy.Checker

-- Hard certificates induce paths; preferences require promotion evidence.
import Metonymy.EndToEnd

-- Executable binding from runtime GF function identifiers and checked
-- certificates to concrete grammatical cells and paths.
import Metonymy.RuntimeBridge

-- A concrete inhabited model showing hard paths and promoted preferences.
import Metonymy.FormalExample

-- Concrete GF-tree/KB instance with a certified hard path, promoted
-- preference, nonconstant semantics, and non-collapse witness.
import Metonymy.RuntimeModel

-- Lexicalized contextual constraints, finite-snapshot obstruction checks,
-- and their sound and complete Boolean reflection.
import Metonymy.Contextual
import Metonymy.ContextualTower
import Metonymy.ContextualModel

-- Filtered positive contexts form a contravariant family of cubical types;
-- checked paths are a natural section, extension is a decidable lifting
-- problem, and compatibility compression is functorial.
import Metonymy.FilteredContext

-- Soundness of cumulative positive GF-subtree compilation and the
-- non-filtering semantics of unpromoted selectional preferences.
import Metonymy.CompilerSoundness

-- Instantiation of the filtered theorem with the executable finite checker
-- and proof-carrying runtime candidates.
import Metonymy.FilteredRuntime

-- Proof-relevant compatibility quotient followed by 2-groupoid truncation,
-- with refinement maps, 2-cell realization, and compression naturality.
import Metonymy.TwoTruncatedContext

-- Executable runtime instantiation with identity compatibility and explicit
-- coherence between parallel compatibility paths.
import Metonymy.TwoTruncatedRuntime

-- Concrete real-data instance of 2-truncated compression: two distinct
-- real Wikidata entities (Novalis's two literary works) genuinely
-- identified at the coarse level by a non-trivial (same-source,
-- same-relation) compatibility relation, with 2-cell coherence realized.
import Metonymy.NovalisCoarseModel

-- A second such instance: Eswatini's two real cabinet formations
-- (GovernedBy), identified at the coarse level by the same shape of
-- compatibility relation.
import Metonymy.EswatiniCoarseModel

-- A third such instance, at a non-empty context: HNK Rijeka and NK
-- Orijent (InstitutionOf), identified at the coarse level once the
-- sentence's own "season" constraint is already satisfied by both.
import Metonymy.RijekaCoarseModel

-- The general, engine-exposed compatibility checker (Checker.
-- compatibilityCheck) instantiated as a genuine CompatibilitySystem for
-- any knowledge base: reproduces the three examples above through one
-- reusable definition, and proves the safety property that motivated
-- restricting it to a single HasSort -- Waterloo's own two heterogeneous
-- organizations (a university, a city council), which satisfy only a
-- broad AnyOf requirement, are correctly rejected, not merged.
import Metonymy.GeneralCoarseCompatibility

-- Concrete directed ontology with two coherent expansion routes and a
-- compatibility quotient that provably separates an unrelated reading.
import Metonymy.ConcreteOntology
