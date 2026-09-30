-- | Pure rendering of a contextual-fiber/contraction result into the
-- same line-oriented, per-layer text format the `contextual-fiber`/
-- `contextual-contract` CLI commands (engine/app/Main.hs) have always
-- printed. Factored out so both that CLI and the whole-database report
-- tool (engine/app/Report.hs) share one rendering, rather than the tool
-- re-implementing a second, possibly drifting copy.
--
-- 'renderFiberReport'/'renderContractionReport' keep the CLI's original,
-- unlabeled output byte-for-byte -- several Python integration tests
-- (auxiliary/tests/evaluation/test_{qid_fiber,run_contextual_corpus,
-- run_automatic_contextual_pipeline}.py) scrape that exact text, so it
-- cannot change. The self-sufficiency additions (a reconstructed
-- sentence line, and entity ids rendered with their snapshot label) are
-- a separate pair of renderers, 'renderFiberReportLabeled'/
-- 'renderContractionReportLabeled', used only by the standalone
-- `metonymy-report` tool against the curated example database -- never
-- by the CLI those tests invoke.
module Metonymy.Report
  ( renderFiberReport
  , renderContractionReport
  , renderFiberReportLabeled
  , renderContractionReportLabeled
  , reconstructSentence
  ) where

import Data.List (intercalate, sortOn)
import Metonymy.Contextual
import Metonymy.ContextualChecked (CoarseReading (..), ContextualContraction (..))
import Metonymy.Ontology (KnowledgeBase, entityLabel, lookupEntity)
import Metonymy.Types

renderFiberReport :: Bool -> Context -> [FiberStage] -> [String]
renderFiberReport formalFiltering context stages =
  [ "source="
      <> show (contextSource context)
      <> " action="
      <> contextAction context
      <> " role="
      <> show (contextRole context)
  ]
    <> concatMap (renderStage formalFiltering show) stages

renderStage :: Bool -> (EntityId -> String) -> FiberStage -> [String]
renderStage formalFiltering render stage =
  [ "stage="
      <> show (stageIndex stage)
      <> " constraint="
      <> maybe "graph-related" renderConstraint (stageConstraint stage)
  , "  survivors="
      <> bracketed (map (render . fineTarget . contextualFineMeaning) (stageCandidates stage))
  , "  agda-layer-check="
      <> if formalFiltering then "true" else "disabled"
  ]
    <> map (("  obstruction=" <>) . show) (stageObstructions stage)
    <> case stageConstraint stage of
      Just constraint
        | payloadIsPreference (constraintPayload constraint) ->
            [ "  preferred="
                <> bracketed
                  ( map
                      (render . fineTarget . contextualFineMeaning)
                      (stagePreferredCandidates stage)
                  )
            ]
              <> map
                (("  preference-miss=" <>) . show)
                (stagePreferenceMisses stage)
      _ -> []

-- | Renders a list of already-rendered entity strings as a bracketed,
-- comma-joined list with no quoting -- "[Q1,Q2]", not "[\"Q1\",\"Q2\"]".
-- 'show' on '[String]' would add per-element quotes (Haskell's String
-- Show instance), which the CLI's original '[EntityId]' rendering never
-- had (its custom 'Show EntityId' instance is just the bare id).
bracketed :: [String] -> String
bracketed xs = "[" <> intercalate "," xs <> "]"

renderConstraint :: ContextConstraint -> String
renderConstraint constraint =
  show (constraintPayload constraint)
    <> "@"
    <> anchorLemma (constraintOrigin constraint)

renderContractionReport :: Bool -> ContextualContraction -> [String]
renderContractionReport formalFiltering result =
  [ "contract="
      <> show (contractionTarget result)
      <> " -> "
      <> show (contractionSource result)
      <> " safety="
      <> contractionSafety result
  ]
    <> concatMap (renderContractionStage formalFiltering show) (contractionStages result)

renderContractionStage :: Bool -> (EntityId -> String) -> FiberStage -> [String]
renderContractionStage formalFiltering render stage =
  [ "stage="
      <> show (stageIndex stage)
      <> " constraint="
      <> maybe "graph-related" renderConstraint (stageConstraint stage)
  , "  survivors="
      <> bracketed (map render (stageTargets stage))
  , "  agda-layer-check="
      <> if formalFiltering then "true" else "disabled"
  ]
    <> case stageConstraint stage of
      Just constraint
        | payloadIsPreference (constraintPayload constraint) ->
            [ "  preferred="
                <> bracketed
                  ( map
                      (render . fineTarget . contextualFineMeaning)
                      (stagePreferredCandidates stage)
                  )
            ]
      _ -> []

-- | Every lexical anchor in a tree, in the order they appear in the
-- source text (by start offset) -- the same anchors validateContext
-- already requires to have valid, non-overlapping-with-nothing spans
-- for the curated example database's hand-built trees. (Automatically
-- constructed trees, such as the Stanza-based pipeline's, may anchor
-- overlapping spans for nested constituents; 'reconstructSentence' is
-- therefore only used against the curated database, never against
-- those.)
allAnchors :: LexicalTree -> [LexicalAnchor]
allAnchors (LexicalLeaf anchor _) = [anchor]
allAnchors (LexicalApply _ children) = concatMap allAnchors children

-- | An approximate rendering of the sentence a Context's LexicalTree
-- was built from: every anchor's surface form, in source order. Not a
-- guarantee of grammatical, publication-quality English (a hand-built
-- tree can anchor a simplified paraphrase of the real corpus sentence,
-- as most flagship examples' module docstrings already say plainly),
-- but always a faithful rendering of what the tower actually
-- lexicalized and checked -- never invented or looked up separately.
reconstructSentence :: Context -> String
reconstructSentence context =
  unwords (map anchorSurface (sortOn anchorStart (allAnchors (contextTree context))))

labelFor :: KnowledgeBase -> EntityId -> String
labelFor kb identifier =
  case lookupEntity kb identifier of
    Just info -> entityLabel info <> " (" <> unEntityId identifier <> ")"
    Nothing -> unEntityId identifier

renderFiberReportLabeled ::
  Bool -> KnowledgeBase -> Context -> [FiberStage] -> Maybe CoarseReading -> [String]
renderFiberReportLabeled formalFiltering kb context stages coarseReading =
  [ "sentence=" <> show (reconstructSentence context)
  , "source="
      <> labelFor kb (contextSource context)
      <> " action="
      <> contextAction context
      <> " role="
      <> show (contextRole context)
  ]
    <> concatMap (renderStage formalFiltering (labelFor kb)) stages
    <> renderCoarseReading kb coarseReading

-- | Only printed when 'Metonymy.ContextualChecked.contextualCoarseReading'
-- proposed a reading AND the compiled Agda checker independently agreed
-- with every pairing -- see that function's own docs for exactly when
-- this can happen (a final stage narrowed by a single, specific HasSort,
-- never a broader AnyOf/AllOf).
renderCoarseReading :: KnowledgeBase -> Maybe CoarseReading -> [String]
renderCoarseReading _ Nothing = []
renderCoarseReading kb (Just reading) =
  [ "coarse-reading="
      <> show (coarseReadingSort reading)
      <> " "
      <> show (map (labelFor kb) (coarseReadingMembers reading))
      <> " (Agda-verified)"
  ]

renderContractionReportLabeled :: Bool -> KnowledgeBase -> ContextualContraction -> [String]
renderContractionReportLabeled formalFiltering kb result =
  [ "contract="
      <> labelFor kb (contractionTarget result)
      <> " -> "
      <> labelFor kb (contractionSource result)
      <> " safety="
      <> contractionSafety result
  ]
    <> concatMap (renderContractionStage formalFiltering (labelFor kb)) (contractionStages result)
