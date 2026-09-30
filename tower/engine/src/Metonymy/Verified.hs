module Metonymy.Verified
  ( verifyContextLayerWithAgda
  , verifyPreferenceLayerWithAgda
  , verifyCompatibilityWithAgda
  ) where

import qualified Data.Text as Text
import qualified Metonymy.CheckerAPI as Agda
import Metonymy.Contextual
import Metonymy.Ontology
import Metonymy.Types

verifyContextLayerWithAgda :: Snapshot -> Context -> EntityId -> Bool
verifyContextLayerWithAgda snapshot context candidate =
  Agda.contextLayerCheck
    (toAgdaKnowledgeBase (snapshotKnowledgeBase snapshot) [])
    (text (snapshotHash snapshot))
    (toAgdaContext context)
    (text (show candidate))

verifyPreferenceLayerWithAgda ::
  Snapshot ->
  ContextConstraint ->
  EntityId ->
  Bool
verifyPreferenceLayerWithAgda snapshot constraint candidate =
  Agda.contextPreferenceCheck
    (toAgdaKnowledgeBase (snapshotKnowledgeBase snapshot) [])
    (toAgdaContextConstraint constraint)
    (text (show candidate))

-- | Independently re-verifies, via the compiled Agda
-- Checker.compatibilityCheck, that two candidates reached from the same
-- source by the same bridge relation, and selected by the same single
-- HasSort requirement, may be reported as one coarse reading -- the
-- engine's own proposal is untrusted until Agda agrees, exactly as for
-- 'verifyContextLayerWithAgda'. Only the two fields compatibilityCheck
-- actually reads (the requirement and the first bridge edge) need to be
-- real; the certificate's other fields are unused by that check and
-- filled with harmless placeholders.
verifyCompatibilityWithAgda ::
  Requirement -> EntityId -> Relation -> EntityId -> Relation -> EntityId -> Bool
verifyCompatibilityWithAgda requirement source leftRelation leftTarget rightRelation rightTarget =
  Agda.compatibilityCheck
    (minimalCertificate leftRelation leftTarget)
    (minimalCertificate rightRelation rightTarget)
  where
    minimalCertificate relation target =
      Agda.rawCertificate
        Agda.expand
        (Agda.forgetContext False False False False False False False)
        (text "")
        Agda.objectHole
        (text (show source))
        (text (show target))
        (toAgdaRequirement requirement)
        (text "")
        (text "")
        [Agda.edge (text (show relation)) (text (show source)) (text (show target))]

toAgdaContext :: Context -> Agda.RawContext
toAgdaContext context =
  Agda.rawContext
    (text (contextSnapshotHash context))
    (text (contextAction context))
    (map toAgdaContextConstraint (contextConstraints context))
    (map text (contextRuleProvenance context))

toAgdaContextConstraint :: ContextConstraint -> Agda.RawContextConstraint
toAgdaContextConstraint constraint =
  Agda.rawContextConstraint
    (toAgdaAnchor (constraintOrigin constraint))
    (case constraintPayload constraint of
      Requires requirement -> Agda.rawRequires (toAgdaRequirement requirement)
      RequiresRelation relation target ->
        Agda.rawRequiresRelation (text (show relation)) (text (show target))
      RequiresSome relation requirement ->
        Agda.rawRequiresSome
          (text (show relation))
          (toAgdaRequirement requirement)
      Prefers requirement ->
        Agda.rawPrefers (toAgdaRequirement requirement)
      PrefersRelation relation target ->
        Agda.rawPrefersRelation
          (text (show relation))
          (text (show target))
      PrefersSome relation requirement ->
        Agda.rawPrefersSome
          (text (show relation))
          (toAgdaRequirement requirement)
    )
    (text (constraintProvenance constraint))

toAgdaAnchor :: LexicalAnchor -> Agda.RawLexicalAnchor
toAgdaAnchor anchor =
  Agda.rawLexicalAnchor
    (text (anchorGFConstructor anchor))
    (text (anchorLemma anchor))
    (text (anchorSurface anchor))
    (fromIntegral (anchorStart anchor))
    (fromIntegral (anchorEnd anchor))

toAgdaKnowledgeBase ::
  KnowledgeBase ->
  [Predicate] ->
  Agda.KnowledgeBase
toAgdaKnowledgeBase knowledgeBase predicates =
  Agda.knowledgeBase
    (map toTypeFact (typeAssertions knowledgeBase))
    (map toRelationFact (relationAssertions knowledgeBase))
    (map toSubsortRule (subsortRules knowledgeBase))
    (map toPredicateFact predicates)
    (map toLexemeFact (entities knowledgeBase))

toLexemeFact :: EntityInfo -> Agda.LexemeFact
toLexemeFact info =
  Agda.lexemeFact
    (text (entityGF info))
    (text (show (entityId info)))

toTypeFact :: TypeAssertion -> Agda.TypeFact
toTypeFact assertion =
  Agda.typeFact
    (text (show (typedEntity assertion)))
    (text (show (assertedSort assertion)))

toRelationFact :: RelationAssertion -> Agda.RelationFact
toRelationFact assertion =
  Agda.relationFact
    (text (show (assertedRelation assertion)))
    (text (show (relationSource assertion)))
    (text (show (relationTarget assertion)))

toSubsortRule :: (Sort, Sort, String) -> Agda.SubsortRule
toSubsortRule (subsort, supersort, _) =
  Agda.subsortRule
    (text (show subsort))
    (text (show supersort))

toPredicateFact :: Predicate -> Agda.PredicateFact
toPredicateFact predicate =
  Agda.predicateFact
    (text (gfFunction predicate))
    (toAgdaRequirement (subjectRequirement predicate))
    (toAgdaRequirement (objectRequirement predicate))
    (text (show (predicateStrength predicate)))
    (text (predicateProvenance predicate))

toAgdaRequirement :: Requirement -> Agda.Requirement
toAgdaRequirement (HasSort sort) = Agda.hasSort (text (show sort))
toAgdaRequirement (AllOf requirements) =
  Agda.allOf (map toAgdaRequirement requirements)
toAgdaRequirement (AnyOf requirements) =
  Agda.anyOf (map toAgdaRequirement requirements)
toAgdaRequirement (Not requirement) =
  Agda.notRequirement (toAgdaRequirement requirement)

text :: String -> Text.Text
text = Text.pack
