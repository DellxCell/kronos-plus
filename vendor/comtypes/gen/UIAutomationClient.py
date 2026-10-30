from enum import IntFlag

import comtypes.gen._944DE083_8FB8_45CF_BCB7_C477ACB2F897_0_1_0 as __wrapper_module__
from comtypes.gen._944DE083_8FB8_45CF_BCB7_C477ACB2F897_0_1_0 import (
    UIA_HyperlinkControlTypeId, UIA_TransformPattern2Id,
    UIA_IsSpreadsheetPatternAvailablePropertyId,
    WindowInteractionState_BlockedByModalWindow,
    IUIAutomationEventHandlerGroup, UIA_IsActiveAttributeId,
    UIA_ValueValuePropertyId, UIA_TextEdit_TextChangedEventId,
    UIA_MultipleViewSupportedViewsPropertyId,
    AnnotationType_ConflictingChange, StyleId_Normal, BSTR,
    UIA_LabeledByPropertyId, UIA_SelectionItemPatternId,
    StyleId_Heading7, UIA_FullDescriptionPropertyId,
    UIA_DataItemControlTypeId, UIA_MarginBottomAttributeId,
    UIA_FrameworkIdPropertyId, IUIAutomationFocusChangedEventHandler,
    ScrollAmount_LargeIncrement, UIA_GridPatternId, HeadingLevel7,
    UIA_SystemAlertEventId, StyleId_Emphasis, HRESULT,
    IUIAutomationDockPattern, UIA_ToolTipControlTypeId,
    UIA_StrikethroughColorAttributeId, CUIAutomation8,
    UIA_GridColumnCountPropertyId, NotificationKind_Other,
    CUIAutomation, UIA_RangeValueValuePropertyId,
    AnnotationType_Sensitive, UIA_SpinnerControlTypeId,
    AnnotationType_MoveChange, TextUnit_Word,
    NotificationProcessing_ImportantAll,
    UIA_NativeWindowHandlePropertyId, IUIAutomationTextEditPattern,
    IUIAutomationTablePattern, UIA_FormLandmarkTypeId,
    UIA_MenuModeEndEventId, IUIAutomationRangeValuePattern,
    PropertyConditionFlags_None, ScrollAmount_SmallIncrement,
    UIA_IsRequiredForFormPropertyId, IUIAutomationWindowPattern,
    TextEditChangeType_None,
    ConnectionRecoveryBehaviorOptions_Enabled,
    UIA_AnnotationDateTimePropertyId, IUIAutomationTextPattern,
    UIA_ScrollHorizontalViewSizePropertyId, ExtendedProperty,
    UIA_HeaderItemControlTypeId, UIA_IsPeripheralPropertyId,
    UIA_OptimizeForVisualContentPropertyId, UIA_MenuBarControlTypeId,
    IUIAutomationProxyFactory, UIA_ClassNamePropertyId,
    UIA_ButtonControlTypeId,
    UIA_IsCustomNavigationPatternAvailablePropertyId,
    UIA_CustomNavigationPatternId, UIA_InvokePatternId,
    UIA_IsObjectModelPatternAvailablePropertyId,
    NotificationProcessing_MostRecent,
    UIA_TransformCanRotatePropertyId,
    ProviderOptions_ProviderOwnsSetFocus,
    UIA_RangeValueMinimumPropertyId,
    UIA_IsMultipleViewPatternAvailablePropertyId,
    UIA_LegacyIAccessibleHelpPropertyId, StyleId_Title,
    UIA_Selection2ItemCountPropertyId,
    UIA_GridItemContainingGridPropertyId, UIA_TextPattern2Id,
    IUIAutomationElement7, ConnectionRecoveryBehaviorOptions_Disabled,
    UIA_ImageControlTypeId, NotificationKind_ActionCompleted,
    UIA_LineSpacingAttributeId, IUIAutomationBoolCondition,
    UIA_TabControlTypeId, TreeScope_Subtree,
    UIA_HostedFragmentRootsInvalidatedEventId,
    UIA_WindowCanMaximizePropertyId, UIA_MenuModeStartEventId,
    UIA_AriaRolePropertyId, NavigateDirection_NextSibling,
    UIA_IsSelectionItemPatternAvailablePropertyId,
    ExpandCollapseState_LeafNode, UIA_AcceleratorKeyPropertyId,
    StructureChangeType_ChildrenInvalidated,
    UIA_IsStylesPatternAvailablePropertyId, StyleId_Heading6,
    TextUnit_Line, SupportedTextSelection_Single,
    UIA_LegacyIAccessibleDefaultActionPropertyId,
    UIA_IndentationTrailingAttributeId,
    UIA_ScrollVerticallyScrollablePropertyId, StyleId_Heading5,
    UIA_IsTextPattern2AvailablePropertyId, TreeScope_Parent,
    UIA_WindowIsTopmostPropertyId, UIA_StylesShapePropertyId,
    UIA_MenuItemControlTypeId, UIA_TableRowOrColumnMajorPropertyId,
    UIA_SpreadsheetPatternId, UIA_CaretBidiModeAttributeId,
    UIA_IsDragPatternAvailablePropertyId,
    ProviderOptions_OverrideProvider, HeadingLevel_None,
    UIA_SummaryChangeId, UIA_RangeValueSmallChangePropertyId,
    IUIAutomationCustomNavigationPattern,
    SynchronizedInputType_KeyDown, SynchronizedInputType_LeftMouseUp,
    IUIAutomationElement6, VARIANT,
    UIA_IsSpreadsheetItemPatternAvailablePropertyId,
    TextPatternRangeEndpoint_End, UIA_ValuePatternId, ToggleState_On,
    UIA_Window_WindowClosedEventId, UIA_ChangesEventId,
    UIA_GridItemColumnSpanPropertyId, AnnotationType_DeletionChange,
    UIA_MarginTopAttributeId,
    UIA_SelectionCanSelectMultiplePropertyId,
    IUIAutomationTextRangeArray, UIA_MenuControlTypeId,
    UIA_DataGridControlTypeId,
    UIA_Selection2LastSelectedItemPropertyId, UIA_DragPatternId,
    IUIAutomationStructureChangedEventHandler,
    IUIAutomationExpandCollapsePattern, UIA_DropTarget_DroppedEventId,
    TreeScope_Descendants, UIA_TableItemRowHeaderItemsPropertyId,
    IUIAutomationStylesPattern, UIA_RangeValueMaximumPropertyId,
    UIA_CalendarControlTypeId, UIA_NotificationEventId,
    UIA_CustomControlTypeId, UIA_SliderControlTypeId,
    UIA_AsyncContentLoadedEventId, IUIAutomationElement5,
    NotificationProcessing_ImportantMostRecent,
    UIA_OrientationPropertyId, UIA_TextControlTypeId,
    IUIAutomationPropertyChangedEventHandler, DockPosition_None,
    UIA_TabItemControlTypeId, UIA_UnderlineColorAttributeId,
    UIA_ComboBoxControlTypeId,
    UIA_LegacyIAccessibleDescriptionPropertyId,
    IUIAutomationDropTargetPattern, UIA_DescribedByPropertyId,
    UIA_VisualEffectsPropertyId, IUIAutomationTextRange3,
    UIA_GridRowCountPropertyId,
    UIA_SelectionItem_ElementSelectedEventId, UIA_TabsAttributeId,
    UIA_Transform2CanZoomPropertyId,
    IUIAutomationSynchronizedInputPattern,
    NotificationProcessing_ImportantCurrentThenMostRecent,
    UIA_InputReachedOtherElementEventId, UIA_StylesPatternId,
    UIA_ToolBarControlTypeId, UIA_StrikethroughStyleAttributeId,
    NotificationKind_ItemAdded, IUIAutomation4,
    UIA_LegacyIAccessibleChildIdPropertyId,
    UIA_SpreadsheetItemFormulaPropertyId,
    UIA_Transform2ZoomMinimumPropertyId,
    UIA_ValueIsReadOnlyPropertyId, IUIAutomationTableItemPattern,
    UIA_SelectionItemSelectionContainerPropertyId,
    UIA_ProcessIdPropertyId, UIA_NamePropertyId, HeadingLevel3,
    IUIAutomationProxyFactoryMapping,
    UIA_AfterParagraphSpacingAttributeId, IUIAutomationTreeWalker,
    AnnotationType_AdvancedProofingIssue,
    CoalesceEventsOptions_Disabled, UIA_CulturePropertyId,
    UIA_BoundingRectanglePropertyId, StyleId_Heading3,
    UIA_AutomationFocusChangedEventId, COMMETHOD,
    ExpandCollapseState_Expanded, IUIAutomationAnnotationPattern,
    UIA_SelectionSelectionPropertyId, UIA_StyleNameAttributeId,
    UIA_ForegroundColorAttributeId, UIA_IsSubscriptAttributeId,
    UIA_Invoke_InvokedEventId, TextUnit_Paragraph,
    ProviderOptions_UseClientCoordinates,
    UIA_Window_WindowOpenedEventId, OrientationType_None,
    UIA_GroupControlTypeId, UIA_StylesFillPatternColorPropertyId,
    UIA_CaretPositionAttributeId, UiaChangeInfo,
    ScrollAmount_SmallDecrement, IUIAutomationElementArray,
    UIA_OverlineStyleAttributeId, AnnotationType_InsertionChange,
    UIA_NavigationLandmarkTypeId, TextPatternRangeEndpoint_Start,
    UIA_ControllerForPropertyId, AnnotationType_FormulaError,
    UIA_AnnotationAuthorPropertyId, AnnotationType_Author,
    UIA_RadioButtonControlTypeId, UIA_ScrollPatternId,
    UIA_TextChildPatternId, UIA_LocalizedControlTypePropertyId,
    IUIAutomationSpreadsheetItemPattern,
    UIA_MultipleViewCurrentViewPropertyId, StyleId_Heading4,
    HeadingLevel6, UIA_HorizontalTextAlignmentAttributeId,
    UIA_Text_TextSelectionChangedEventId, UIA_HeadingLevelPropertyId,
    WindowInteractionState_ReadyForUserInteraction,
    UIA_DragDropEffectPropertyId, StyleId_Heading1,
    UIA_GridItemRowSpanPropertyId, Polite, HeadingLevel8,
    UIA_LiveSettingPropertyId, UIA_TableRowHeadersPropertyId,
    UIA_OutlineColorPropertyId, UIA_Drag_DragCancelEventId,
    IAccessible, WindowVisualState_Normal, UIA_ListControlTypeId,
    StyleId_Heading9, StructureChangeType_ChildrenReordered,
    IUIAutomationProxyFactoryEntry, UIA_ProviderDescriptionPropertyId,
    UIA_FlowsFromPropertyId, IUIAutomationChangesEventHandler,
    ExpandCollapseState_Collapsed, UIA_Drag_DragStartEventId,
    UIA_CheckBoxControlTypeId, UIA_MenuClosedEventId,
    UIA_ScrollVerticalScrollPercentPropertyId, UIA_GridItemPatternId,
    UIA_TitleBarControlTypeId, DockPosition_Top,
    IUIAutomationDragPattern, IUIAutomationElement3,
    TreeTraversalOptions_LastToFirstOrder,
    UIA_LegacyIAccessiblePatternId, UIA_BackgroundColorAttributeId,
    NotificationProcessing_CurrentThenMostRecent,
    UIA_TableItemColumnHeaderItemsPropertyId,
    IUIAutomationOrCondition, IUIAutomationSelectionPattern, WSTRING,
    UIA_DockDockPositionPropertyId,
    UIA_LegacyIAccessibleStatePropertyId,
    UIA_AnnotationTargetPropertyId, UIA_Transform2ZoomLevelPropertyId,
    IUIAutomationEventHandler,
    UIA_IsAnnotationPatternAvailablePropertyId,
    UIA_ExpandCollapsePatternId, UIA_MultipleViewPatternId,
    UIA_LayoutInvalidatedEventId,
    UIA_SpreadsheetItemAnnotationObjectsPropertyId,
    UIA_LegacyIAccessibleValuePropertyId, IUIAutomationTextRange,
    SynchronizedInputType_LeftMouseDown,
    UIA_Transform2ZoomMaximumPropertyId, DockPosition_Right,
    UIA_TablePatternId, IUIAutomationGridPattern,
    UIA_GridItemColumnPropertyId, UIA_SeparatorControlTypeId,
    UIA_DocumentControlTypeId, RowOrColumnMajor_ColumnMajor,
    NavigateDirection_Parent, UIA_DragDropEffectsPropertyId,
    UIA_IndentationLeadingAttributeId, IUIAutomationAndCondition,
    UIA_SayAsInterpretAsMetadataId, UIA_InputReachedTargetEventId,
    UIA_IsTextPatternAvailablePropertyId, AnnotationType_GrammarError,
    UIA_ScrollHorizontallyScrollablePropertyId,
    UIA_IsTablePatternAvailablePropertyId,
    IUIAutomationObjectModelPattern, StyleId_BulletedList,
    UIA_IsInvokePatternAvailablePropertyId,
    TextEditChangeType_CompositionFinalized, UIA_HeaderControlTypeId,
    AutomationElementMode_Full, HeadingLevel5,
    UIA_LiveRegionChangedEventId, AnnotationType_DataValidationError,
    UIA_RangeValueLargeChangePropertyId,
    TreeTraversalOptions_PostOrder,
    UIA_IsRangeValuePatternAvailablePropertyId,
    UIA_SelectionIsSelectionRequiredPropertyId,
    UIA_SpreadsheetItemAnnotationTypesPropertyId,
    UIA_WindowWindowInteractionStatePropertyId,
    OrientationType_Vertical, UIA_FontWeightAttributeId,
    AnnotationType_TrackChanges,
    UIA_DropTargetDropTargetEffectsPropertyId,
    UIA_StylesFillColorPropertyId, IUIAutomationTextRange2,
    UIA_SelectionPatternId,
    UIA_IsSynchronizedInputPatternAvailablePropertyId, IUIAutomation2,
    Off, UIA_AnnotationTypesAttributeId,
    WindowInteractionState_NotResponding, WindowVisualState_Maximized,
    WindowInteractionState_Running,
    UIA_IsSelectionPattern2AvailablePropertyId,
    UIA_IsGridItemPatternAvailablePropertyId,
    UIA_TransformCanMovePropertyId, NavigateDirection_PreviousSibling,
    UIA_AnnotationPatternId, UIA_AnnotationTypesPropertyId,
    UIA_ListItemControlTypeId, UIA_SemanticZoomControlTypeId,
    UIA_AnnotationAnnotationTypeNamePropertyId,
    AnnotationType_ExternalChange, IUnknown, UIA_StyleIdAttributeId,
    UIA_AutomationIdPropertyId, AnnotationType_CircularReferenceError,
    OrientationType_Horizontal, UIA_TextPatternId,
    UIA_ItemContainerPatternId, TextUnit_Page, tagPOINT,
    IUIAutomationTogglePattern, UIA_StatusBarControlTypeId,
    UIA_Selection_InvalidatedEventId,
    UIA_IsTextChildPatternAvailablePropertyId,
    UIA_IsSelectionPatternAvailablePropertyId, IUIAutomationElement,
    tagRECT, HeadingLevel9, UIA_SizePropertyId, GUID,
    DockPosition_Left, PropertyConditionFlags_IgnoreCase,
    AnnotationType_Header, UIA_TableControlTypeId, TreeScope_Children,
    IUIAutomation3, AnnotationType_Footnote, HeadingLevel1,
    UIA_IsReadOnlyAttributeId, RowOrColumnMajor_RowMajor,
    UIA_TogglePatternId, _check_version, UIA_EditControlTypeId,
    UIA_RangeValuePatternId, StyleId_Subtitle,
    UIA_LegacyIAccessibleKeyboardShortcutPropertyId,
    UIA_HasKeyboardFocusPropertyId, UIA_ItemStatusPropertyId,
    UIA_ObjectModelPatternId, RowOrColumnMajor_Indeterminate,
    UIA_AutomationPropertyChangedEventId, IUIAutomation5,
    AnnotationType_Endnote,
    UIA_TextEdit_ConversionTargetChangedEventId,
    UIA_AnnotationObjectsAttributeId, UIA_DropTargetPatternId,
    UIA_TableItemPatternId, SupportedTextSelection_Multiple,
    UIA_IsWindowPatternAvailablePropertyId,
    SynchronizedInputType_KeyUp, TextUnit_Character,
    ZoomUnit_NoAmount, UIA_WindowPatternId,
    IUIAutomationSelectionItemPattern, Assertive,
    TreeTraversalOptions_Default, UIA_LegacyIAccessibleRolePropertyId,
    _midlSAFEARRAY, UIA_TableColumnHeadersPropertyId,
    CoalesceEventsOptions_Enabled, AnnotationType_FormatChange,
    UIA_RuntimeIdPropertyId, CoClass, ToggleState_Indeterminate,
    IUIAutomationPropertyCondition, AutomationElementMode_None,
    typelib_path, TreeScope_Element, UIA_FillColorPropertyId,
    UIA_ScrollItemPatternId, UIA_IsGridPatternAvailablePropertyId,
    UIA_SpreadsheetItemPatternId, IUIAutomationTextPattern2,
    UIA_IsValuePatternAvailablePropertyId,
    UIA_DropTarget_DragLeaveEventId, NavigateDirection_LastChild,
    UIA_ProgressBarControlTypeId,
    PropertyConditionFlags_MatchSubstring, StyleId_NumberedList,
    IUIAutomationElement2, IUIAutomation, UIA_ToolTipClosedEventId,
    UIA_IsTransformPatternAvailablePropertyId, IDispatch,
    UIA_ItemTypePropertyId, WindowInteractionState_Closing,
    UIA_HelpTextPropertyId, UIA_IsOffscreenPropertyId,
    UIA_SelectionPattern2Id, UIA_BeforeParagraphSpacingAttributeId,
    UIA_LinkAttributeId, WindowVisualState_Minimized,
    ProviderOptions_HasNativeIAccessible,
    IUIAutomationSelectionPattern2, UIA_SplitButtonControlTypeId,
    IUIAutomationElement4, IUIAutomationCacheRequest,
    ZoomUnit_SmallIncrement,
    UIA_IsDropTargetPatternAvailablePropertyId, AnnotationType_Footer,
    IUIAutomationTransformPattern,
    UIA_IndentationFirstLineAttributeId, UIA_Text_TextChangedEventId,
    UIA_IsScrollItemPatternAvailablePropertyId,
    UIA_IsHiddenAttributeId, IUIAutomationInvokePattern,
    AnnotationType_UnsyncedChange, UIA_IsItalicAttributeId,
    UIA_ClickablePointPropertyId, UIA_WindowIsModalPropertyId,
    StyleId_Heading2, UIA_SizeOfSetPropertyId,
    TextEditChangeType_AutoComplete, UIA_GridItemRowPropertyId,
    UIA_IsItemContainerPatternAvailablePropertyId,
    UIA_IsLegacyIAccessiblePatternAvailablePropertyId,
    NotificationProcessing_All, UIA_SynchronizedInputPatternId,
    IUIAutomationItemContainerPattern, UIA_FontSizeAttributeId,
    UIA_Selection2CurrentSelectedItemPropertyId,
    ProviderOptions_NonClientAreaProvider,
    UIA_IsTransformPattern2AvailablePropertyId,
    UIA_SelectionItem_ElementAddedToSelectionEventId,
    IUIAutomationValuePattern, NotificationKind_ItemRemoved,
    UIA_CapStyleAttributeId, UIA_DragGrabbedItemsPropertyId,
    ProviderOptions_ClientSideProvider, UIA_IsPasswordPropertyId,
    UIA_IsTextEditPatternAvailablePropertyId,
    IUIAutomationSpreadsheetPattern, UIA_AnimationStyleAttributeId,
    TextUnit_Document, ToggleState_Off,
    UIA_ActiveTextPositionChangedEventId, UIA_StylesStyleIdPropertyId,
    UIA_LandmarkTypePropertyId, SynchronizedInputType_RightMouseUp,
    UIA_ThumbControlTypeId, UIA_AppBarControlTypeId,
    UIA_IsTableItemPatternAvailablePropertyId,
    ZoomUnit_LargeDecrement, UIA_SelectionItemIsSelectedPropertyId,
    UIA_Selection2FirstSelectedItemPropertyId,
    ExpandCollapseState_PartiallyExpanded, UIA_SearchLandmarkTypeId,
    UIA_PositionInSetPropertyId, IUIAutomationNotCondition,
    UIA_CustomLandmarkTypeId, StyleId_Custom,
    UIA_IsExpandCollapsePatternAvailablePropertyId,
    UIA_WindowControlTypeId, UIA_RotationPropertyId, TreeScope_None,
    UIA_MenuOpenedEventId, UIA_IsEnabledPropertyId, HeadingLevel4,
    UIA_CultureAttributeId, IUIAutomationGridItemPattern,
    UIA_AriaPropertiesPropertyId, ProviderOptions_UseComThreading,
    NavigateDirection_FirstChild, IUIAutomationScrollItemPattern,
    UIA_StructureChangedEventId, TreeScope_Ancestors,
    UIA_StylesExtendedPropertiesPropertyId,
    UIA_VirtualizedItemPatternId, UIA_LevelPropertyId,
    StructureChangeType_ChildRemoved,
    SynchronizedInputType_RightMouseDown,
    TextEditChangeType_Composition,
    UIA_ScrollVerticalViewSizePropertyId,
    UIA_WindowWindowVisualStatePropertyId, StyleId_Quote, Library,
    UIA_SelectionItem_ElementRemovedFromSelectionEventId,
    UIA_IsDialogPropertyId, UIA_PaneControlTypeId,
    UIA_IsDataValidForFormPropertyId, TextUnit_Format,
    UIA_IsControlElementPropertyId, UIA_OutlineThicknessPropertyId,
    AnnotationType_Highlighted, UIA_InputDiscardedEventId,
    UIA_LocalizedLandmarkTypePropertyId, UIA_CenterPointPropertyId,
    dispid, IUIAutomationScrollPattern, UIA_ScrollBarControlTypeId,
    ZoomUnit_SmallDecrement, UIA_MarginLeadingAttributeId,
    UIA_ToggleToggleStatePropertyId, IUIAutomation6,
    UIA_DragIsGrabbedPropertyId, UIA_LegacyIAccessibleNamePropertyId,
    UIA_AccessKeyPropertyId, IUIAutomationElement8,
    AnnotationType_Unknown, UIA_FontNameAttributeId,
    UIA_StylesFillPatternStylePropertyId,
    UIA_IsKeyboardFocusablePropertyId, IUIAutomationCondition,
    SupportedTextSelection_None,
    UIA_LegacyIAccessibleSelectionPropertyId,
    IUIAutomationTextChildPattern, AnnotationType_SpellingError,
    UIA_ControlTypePropertyId, UIA_StylesStyleNamePropertyId,
    UIA_ToolTipOpenedEventId, IRawElementProviderSimple,
    UIA_TextEditPatternId, UIA_SayAsInterpretAsAttributeId,
    UIA_UnderlineStyleAttributeId, DockPosition_Fill,
    ProviderOptions_RefuseNonClientSupport, UIA_FlowsToPropertyId,
    UIA_OutlineStylesAttributeId, ProviderOptions_ServerSideProvider,
    UIA_IsContentElementPropertyId, AnnotationType_Mathematics,
    UIA_TransformPatternId, _lcid, UIA_BulletStyleAttributeId,
    UIA_TransformCanResizePropertyId, UIA_TreeItemControlTypeId,
    StyleId_Heading8, UIA_ScrollHorizontalScrollPercentPropertyId,
    UIA_MainLandmarkTypeId, AnnotationType_EditingLockedChange,
    StructureChangeType_ChildAdded, ZoomUnit_LargeIncrement,
    NotificationKind_ActionAborted, UIA_Drag_DragCompleteEventId,
    UIA_AnnotationAnnotationTypeIdPropertyId,
    UIA_TextFlowDirectionsAttributeId, UIA_DockPatternId,
    IUIAutomationTextEditTextChangedEventHandler,
    IUIAutomationNotificationEventHandler, IUIAutomationElement9,
    UIA_IsTogglePatternAvailablePropertyId,
    UIA_MarginTrailingAttributeId, UIA_WindowCanMinimizePropertyId,
    UIA_ExpandCollapseExpandCollapseStatePropertyId,
    UIA_OverlineColorAttributeId,
    IUIAutomationLegacyIAccessiblePattern, ScrollAmount_NoAmount,
    IUIAutomationVirtualizedItemPattern, DockPosition_Bottom,
    UIA_DropTarget_DragEnterEventId, UIA_TreeControlTypeId,
    UIA_SelectionActiveEndAttributeId,
    UIA_IsVirtualizedItemPatternAvailablePropertyId,
    UIA_RangeValueIsReadOnlyPropertyId, AnnotationType_Comment,
    IUIAutomationTransformPattern2,
    StructureChangeType_ChildrenBulkAdded, HeadingLevel2,
    ScrollAmount_LargeDecrement,
    UIA_DropTargetDropTargetEffectPropertyId,
    UIA_IsScrollPatternAvailablePropertyId,
    TextEditChangeType_AutoCorrect,
    IUIAutomationActiveTextPositionChangedEventHandler,
    UIA_AnnotationObjectsPropertyId,
    UIA_IsDockPatternAvailablePropertyId, UIA_FillTypePropertyId,
    UIA_IsSuperscriptAttributeId, IUIAutomationMultipleViewPattern,
    StructureChangeType_ChildrenBulkRemoved
)


class TextEditChangeType(IntFlag):
    TextEditChangeType_None = 0
    TextEditChangeType_AutoCorrect = 1
    TextEditChangeType_Composition = 2
    TextEditChangeType_CompositionFinalized = 3
    TextEditChangeType_AutoComplete = 4


class NavigateDirection(IntFlag):
    NavigateDirection_Parent = 0
    NavigateDirection_NextSibling = 1
    NavigateDirection_PreviousSibling = 2
    NavigateDirection_FirstChild = 3
    NavigateDirection_LastChild = 4


class StructureChangeType(IntFlag):
    StructureChangeType_ChildAdded = 0
    StructureChangeType_ChildRemoved = 1
    StructureChangeType_ChildrenInvalidated = 2
    StructureChangeType_ChildrenBulkAdded = 3
    StructureChangeType_ChildrenBulkRemoved = 4
    StructureChangeType_ChildrenReordered = 5


class NotificationKind(IntFlag):
    NotificationKind_ItemAdded = 0
    NotificationKind_ItemRemoved = 1
    NotificationKind_ActionCompleted = 2
    NotificationKind_ActionAborted = 3
    NotificationKind_Other = 4


class NotificationProcessing(IntFlag):
    NotificationProcessing_ImportantAll = 0
    NotificationProcessing_ImportantMostRecent = 1
    NotificationProcessing_All = 2
    NotificationProcessing_MostRecent = 3
    NotificationProcessing_CurrentThenMostRecent = 4
    NotificationProcessing_ImportantCurrentThenMostRecent = 5


class TextPatternRangeEndpoint(IntFlag):
    TextPatternRangeEndpoint_Start = 0
    TextPatternRangeEndpoint_End = 1


class TextUnit(IntFlag):
    TextUnit_Character = 0
    TextUnit_Format = 1
    TextUnit_Word = 2
    TextUnit_Line = 3
    TextUnit_Paragraph = 4
    TextUnit_Page = 5
    TextUnit_Document = 6


class ZoomUnit(IntFlag):
    ZoomUnit_NoAmount = 0
    ZoomUnit_LargeDecrement = 1
    ZoomUnit_SmallDecrement = 2
    ZoomUnit_LargeIncrement = 3
    ZoomUnit_SmallIncrement = 4


class WindowVisualState(IntFlag):
    WindowVisualState_Normal = 0
    WindowVisualState_Maximized = 1
    WindowVisualState_Minimized = 2


class TreeScope(IntFlag):
    TreeScope_None = 0
    TreeScope_Element = 1
    TreeScope_Children = 2
    TreeScope_Descendants = 4
    TreeScope_Parent = 8
    TreeScope_Ancestors = 16
    TreeScope_Subtree = 7


class OrientationType(IntFlag):
    OrientationType_None = 0
    OrientationType_Horizontal = 1
    OrientationType_Vertical = 2


class LiveSetting(IntFlag):
    Off = 0
    Polite = 1
    Assertive = 2


class TreeTraversalOptions(IntFlag):
    TreeTraversalOptions_Default = 0
    TreeTraversalOptions_PostOrder = 1
    TreeTraversalOptions_LastToFirstOrder = 2


class DockPosition(IntFlag):
    DockPosition_Top = 0
    DockPosition_Left = 1
    DockPosition_Bottom = 2
    DockPosition_Right = 3
    DockPosition_Fill = 4
    DockPosition_None = 5


class WindowInteractionState(IntFlag):
    WindowInteractionState_Running = 0
    WindowInteractionState_Closing = 1
    WindowInteractionState_ReadyForUserInteraction = 2
    WindowInteractionState_BlockedByModalWindow = 3
    WindowInteractionState_NotResponding = 4


class ExpandCollapseState(IntFlag):
    ExpandCollapseState_Collapsed = 0
    ExpandCollapseState_Expanded = 1
    ExpandCollapseState_PartiallyExpanded = 2
    ExpandCollapseState_LeafNode = 3


class ProviderOptions(IntFlag):
    ProviderOptions_ClientSideProvider = 1
    ProviderOptions_ServerSideProvider = 2
    ProviderOptions_NonClientAreaProvider = 4
    ProviderOptions_OverrideProvider = 8
    ProviderOptions_ProviderOwnsSetFocus = 16
    ProviderOptions_UseComThreading = 32
    ProviderOptions_RefuseNonClientSupport = 64
    ProviderOptions_HasNativeIAccessible = 128
    ProviderOptions_UseClientCoordinates = 256


class SupportedTextSelection(IntFlag):
    SupportedTextSelection_None = 0
    SupportedTextSelection_Single = 1
    SupportedTextSelection_Multiple = 2


class PropertyConditionFlags(IntFlag):
    PropertyConditionFlags_None = 0
    PropertyConditionFlags_IgnoreCase = 1
    PropertyConditionFlags_MatchSubstring = 2


class ScrollAmount(IntFlag):
    ScrollAmount_LargeDecrement = 0
    ScrollAmount_SmallDecrement = 1
    ScrollAmount_NoAmount = 2
    ScrollAmount_LargeIncrement = 3
    ScrollAmount_SmallIncrement = 4


class AutomationElementMode(IntFlag):
    AutomationElementMode_None = 0
    AutomationElementMode_Full = 1


class ConnectionRecoveryBehaviorOptions(IntFlag):
    ConnectionRecoveryBehaviorOptions_Disabled = 0
    ConnectionRecoveryBehaviorOptions_Enabled = 1


class CoalesceEventsOptions(IntFlag):
    CoalesceEventsOptions_Disabled = 0
    CoalesceEventsOptions_Enabled = 1


class SynchronizedInputType(IntFlag):
    SynchronizedInputType_KeyUp = 1
    SynchronizedInputType_KeyDown = 2
    SynchronizedInputType_LeftMouseUp = 4
    SynchronizedInputType_LeftMouseDown = 8
    SynchronizedInputType_RightMouseUp = 16
    SynchronizedInputType_RightMouseDown = 32


class RowOrColumnMajor(IntFlag):
    RowOrColumnMajor_RowMajor = 0
    RowOrColumnMajor_ColumnMajor = 1
    RowOrColumnMajor_Indeterminate = 2


class ToggleState(IntFlag):
    ToggleState_Off = 0
    ToggleState_On = 1
    ToggleState_Indeterminate = 2


__all__ = [
    'UIA_HyperlinkControlTypeId', 'UIA_TransformPattern2Id',
    'UIA_IsSpreadsheetPatternAvailablePropertyId',
    'WindowInteractionState_BlockedByModalWindow',
    'IUIAutomationEventHandlerGroup', 'UIA_IsActiveAttributeId',
    'UIA_ValueValuePropertyId', 'UIA_TextEdit_TextChangedEventId',
    'UIA_MultipleViewSupportedViewsPropertyId',
    'AnnotationType_ConflictingChange', 'StyleId_Normal',
    'UIA_LabeledByPropertyId', 'UIA_SelectionItemPatternId',
    'StyleId_Heading7', 'SupportedTextSelection',
    'TextEditChangeType', 'UIA_FullDescriptionPropertyId',
    'UIA_DataItemControlTypeId', 'UIA_MarginBottomAttributeId',
    'UIA_FrameworkIdPropertyId',
    'IUIAutomationFocusChangedEventHandler',
    'ScrollAmount_LargeIncrement', 'NotificationKind',
    'UIA_GridPatternId', 'ZoomUnit', 'HeadingLevel7',
    'UIA_SystemAlertEventId', 'StyleId_Emphasis',
    'IUIAutomationDockPattern', 'UIA_ToolTipControlTypeId',
    'UIA_StrikethroughColorAttributeId', 'CUIAutomation8',
    'UIA_GridColumnCountPropertyId', 'NotificationKind_Other',
    'CUIAutomation', 'UIA_RangeValueValuePropertyId',
    'AnnotationType_Sensitive', 'UIA_SpinnerControlTypeId',
    'AnnotationType_MoveChange', 'TextUnit_Word',
    'NotificationProcessing_ImportantAll',
    'UIA_NativeWindowHandlePropertyId',
    'IUIAutomationTextEditPattern', 'IUIAutomationTablePattern',
    'UIA_FormLandmarkTypeId', 'AutomationElementMode',
    'UIA_MenuModeEndEventId', 'IUIAutomationRangeValuePattern',
    'PropertyConditionFlags_None', 'ScrollAmount_SmallIncrement',
    'UIA_IsRequiredForFormPropertyId', 'IUIAutomationWindowPattern',
    'TextEditChangeType_None',
    'ConnectionRecoveryBehaviorOptions_Enabled',
    'UIA_AnnotationDateTimePropertyId', 'IUIAutomationTextPattern',
    'PropertyConditionFlags',
    'UIA_ScrollHorizontalViewSizePropertyId', 'ExtendedProperty',
    'UIA_HeaderItemControlTypeId', 'UIA_IsPeripheralPropertyId',
    'UIA_OptimizeForVisualContentPropertyId',
    'UIA_MenuBarControlTypeId', 'IUIAutomationProxyFactory',
    'UIA_ClassNamePropertyId', 'CoalesceEventsOptions',
    'UIA_ButtonControlTypeId',
    'UIA_IsCustomNavigationPatternAvailablePropertyId',
    'UIA_CustomNavigationPatternId', 'UIA_InvokePatternId',
    'UIA_IsObjectModelPatternAvailablePropertyId',
    'NotificationProcessing_MostRecent',
    'UIA_TransformCanRotatePropertyId',
    'ProviderOptions_ProviderOwnsSetFocus',
    'UIA_RangeValueMinimumPropertyId',
    'UIA_IsMultipleViewPatternAvailablePropertyId',
    'UIA_LegacyIAccessibleHelpPropertyId', 'StyleId_Title',
    'UIA_Selection2ItemCountPropertyId',
    'UIA_GridItemContainingGridPropertyId', 'UIA_TextPattern2Id',
    'IUIAutomationElement7',
    'ConnectionRecoveryBehaviorOptions_Disabled',
    'UIA_ImageControlTypeId', 'NotificationKind_ActionCompleted',
    'UIA_LineSpacingAttributeId', 'IUIAutomationBoolCondition',
    'ScrollAmount', 'WindowVisualState', 'UIA_TabControlTypeId',
    'TreeScope_Subtree', 'UIA_HostedFragmentRootsInvalidatedEventId',
    'UIA_WindowCanMaximizePropertyId', 'UIA_MenuModeStartEventId',
    'UIA_AriaRolePropertyId', 'NavigateDirection_NextSibling',
    'UIA_IsSelectionItemPatternAvailablePropertyId',
    'ExpandCollapseState_LeafNode', 'UIA_AcceleratorKeyPropertyId',
    'StructureChangeType_ChildrenInvalidated',
    'UIA_IsStylesPatternAvailablePropertyId', 'StyleId_Heading6',
    'TextUnit_Line', 'SupportedTextSelection_Single',
    'UIA_LegacyIAccessibleDefaultActionPropertyId',
    'UIA_IndentationTrailingAttributeId',
    'UIA_ScrollVerticallyScrollablePropertyId', 'StyleId_Heading5',
    'UIA_IsTextPattern2AvailablePropertyId', 'TreeScope_Parent',
    'UIA_WindowIsTopmostPropertyId', 'UIA_StylesShapePropertyId',
    'UIA_MenuItemControlTypeId',
    'UIA_TableRowOrColumnMajorPropertyId', 'UIA_SpreadsheetPatternId',
    'UIA_CaretBidiModeAttributeId',
    'UIA_IsDragPatternAvailablePropertyId',
    'ProviderOptions_OverrideProvider', 'HeadingLevel_None',
    'UIA_SummaryChangeId', 'UIA_RangeValueSmallChangePropertyId',
    'IUIAutomationCustomNavigationPattern',
    'SynchronizedInputType_KeyDown',
    'SynchronizedInputType_LeftMouseUp', 'IUIAutomationElement6',
    'UIA_IsSpreadsheetItemPatternAvailablePropertyId',
    'StructureChangeType', 'TextPatternRangeEndpoint_End',
    'UIA_ValuePatternId', 'ToggleState_On',
    'UIA_Window_WindowClosedEventId', 'UIA_ChangesEventId',
    'UIA_GridItemColumnSpanPropertyId',
    'AnnotationType_DeletionChange', 'UIA_MarginTopAttributeId',
    'UIA_SelectionCanSelectMultiplePropertyId',
    'IUIAutomationTextRangeArray', 'NavigateDirection',
    'UIA_MenuControlTypeId', 'UIA_DataGridControlTypeId',
    'UIA_Selection2LastSelectedItemPropertyId', 'UIA_DragPatternId',
    'IUIAutomationStructureChangedEventHandler',
    'IUIAutomationExpandCollapsePattern',
    'UIA_DropTarget_DroppedEventId', 'TreeScope_Descendants',
    'UIA_TableItemRowHeaderItemsPropertyId',
    'IUIAutomationStylesPattern', 'UIA_RangeValueMaximumPropertyId',
    'UIA_CalendarControlTypeId', 'UIA_NotificationEventId',
    'UIA_CustomControlTypeId', 'UIA_SliderControlTypeId',
    'UIA_AsyncContentLoadedEventId', 'IUIAutomationElement5',
    'NotificationProcessing_ImportantMostRecent',
    'UIA_OrientationPropertyId', 'TreeTraversalOptions',
    'UIA_TextControlTypeId',
    'IUIAutomationPropertyChangedEventHandler', 'ToggleState',
    'DockPosition_None', 'UIA_TabItemControlTypeId',
    'UIA_UnderlineColorAttributeId', 'UIA_ComboBoxControlTypeId',
    'UIA_LegacyIAccessibleDescriptionPropertyId',
    'IUIAutomationDropTargetPattern', 'UIA_DescribedByPropertyId',
    'UIA_VisualEffectsPropertyId', 'IUIAutomationTextRange3',
    'UIA_GridRowCountPropertyId',
    'UIA_SelectionItem_ElementSelectedEventId', 'UIA_TabsAttributeId',
    'OrientationType', 'UIA_Transform2CanZoomPropertyId',
    'IUIAutomationSynchronizedInputPattern',
    'NotificationProcessing_ImportantCurrentThenMostRecent',
    'UIA_InputReachedOtherElementEventId', 'UIA_StylesPatternId',
    'UIA_ToolBarControlTypeId', 'UIA_StrikethroughStyleAttributeId',
    'NotificationKind_ItemAdded', 'IUIAutomation4',
    'UIA_LegacyIAccessibleChildIdPropertyId',
    'UIA_SpreadsheetItemFormulaPropertyId',
    'UIA_Transform2ZoomMinimumPropertyId',
    'UIA_ValueIsReadOnlyPropertyId', 'IUIAutomationTableItemPattern',
    'UIA_SelectionItemSelectionContainerPropertyId',
    'UIA_ProcessIdPropertyId', 'UIA_NamePropertyId', 'HeadingLevel3',
    'IUIAutomationProxyFactoryMapping',
    'UIA_AfterParagraphSpacingAttributeId', 'IUIAutomationTreeWalker',
    'AnnotationType_AdvancedProofingIssue',
    'CoalesceEventsOptions_Disabled', 'UIA_CulturePropertyId',
    'UIA_BoundingRectanglePropertyId', 'StyleId_Heading3',
    'UIA_AutomationFocusChangedEventId',
    'ExpandCollapseState_Expanded', 'IUIAutomationAnnotationPattern',
    'UIA_SelectionSelectionPropertyId', 'UIA_StyleNameAttributeId',
    'UIA_ForegroundColorAttributeId', 'UIA_IsSubscriptAttributeId',
    'UIA_Invoke_InvokedEventId', 'TextUnit_Paragraph',
    'ProviderOptions_UseClientCoordinates',
    'UIA_Window_WindowOpenedEventId', 'DockPosition',
    'OrientationType_None', 'UIA_GroupControlTypeId',
    'UIA_StylesFillPatternColorPropertyId',
    'UIA_CaretPositionAttributeId', 'UiaChangeInfo',
    'ScrollAmount_SmallDecrement', 'IUIAutomationElementArray',
    'UIA_OverlineStyleAttributeId', 'AnnotationType_InsertionChange',
    'UIA_NavigationLandmarkTypeId', 'TextPatternRangeEndpoint_Start',
    'UIA_ControllerForPropertyId', 'AnnotationType_FormulaError',
    'UIA_AnnotationAuthorPropertyId', 'AnnotationType_Author',
    'UIA_RadioButtonControlTypeId', 'UIA_ScrollPatternId',
    'UIA_TextChildPatternId', 'UIA_LocalizedControlTypePropertyId',
    'TreeScope', 'IUIAutomationSpreadsheetItemPattern',
    'UIA_MultipleViewCurrentViewPropertyId', 'StyleId_Heading4',
    'HeadingLevel6', 'UIA_HorizontalTextAlignmentAttributeId',
    'UIA_Text_TextSelectionChangedEventId',
    'UIA_HeadingLevelPropertyId',
    'WindowInteractionState_ReadyForUserInteraction',
    'UIA_DragDropEffectPropertyId', 'StyleId_Heading1',
    'UIA_GridItemRowSpanPropertyId', 'Polite', 'HeadingLevel8',
    'UIA_LiveSettingPropertyId', 'UIA_TableRowHeadersPropertyId',
    'UIA_OutlineColorPropertyId', 'UIA_Drag_DragCancelEventId',
    'IAccessible', 'WindowVisualState_Normal',
    'UIA_ListControlTypeId', 'StyleId_Heading9',
    'StructureChangeType_ChildrenReordered',
    'IUIAutomationProxyFactoryEntry',
    'UIA_ProviderDescriptionPropertyId', 'UIA_FlowsFromPropertyId',
    'IUIAutomationChangesEventHandler',
    'ExpandCollapseState_Collapsed', 'UIA_Drag_DragStartEventId',
    'UIA_CheckBoxControlTypeId', 'UIA_MenuClosedEventId',
    'UIA_ScrollVerticalScrollPercentPropertyId',
    'UIA_GridItemPatternId', 'UIA_TitleBarControlTypeId',
    'DockPosition_Top', 'IUIAutomationDragPattern',
    'IUIAutomationElement3', 'TreeTraversalOptions_LastToFirstOrder',
    'UIA_LegacyIAccessiblePatternId',
    'UIA_BackgroundColorAttributeId',
    'NotificationProcessing_CurrentThenMostRecent',
    'UIA_TableItemColumnHeaderItemsPropertyId',
    'IUIAutomationOrCondition', 'IUIAutomationSelectionPattern',
    'UIA_DockDockPositionPropertyId',
    'UIA_LegacyIAccessibleStatePropertyId',
    'UIA_AnnotationTargetPropertyId',
    'UIA_Transform2ZoomLevelPropertyId', 'IUIAutomationEventHandler',
    'UIA_IsAnnotationPatternAvailablePropertyId',
    'UIA_ExpandCollapsePatternId', 'UIA_MultipleViewPatternId',
    'UIA_LayoutInvalidatedEventId',
    'UIA_SpreadsheetItemAnnotationObjectsPropertyId',
    'UIA_LegacyIAccessibleValuePropertyId', 'IUIAutomationTextRange',
    'SynchronizedInputType_LeftMouseDown',
    'UIA_Transform2ZoomMaximumPropertyId', 'DockPosition_Right',
    'UIA_TablePatternId', 'IUIAutomationGridPattern',
    'UIA_GridItemColumnPropertyId', 'UIA_SeparatorControlTypeId',
    'UIA_DocumentControlTypeId', 'RowOrColumnMajor_ColumnMajor',
    'NavigateDirection_Parent', 'UIA_DragDropEffectsPropertyId',
    'UIA_IndentationLeadingAttributeId', 'IUIAutomationAndCondition',
    'ConnectionRecoveryBehaviorOptions',
    'UIA_SayAsInterpretAsMetadataId', 'UIA_InputReachedTargetEventId',
    'UIA_IsTextPatternAvailablePropertyId',
    'AnnotationType_GrammarError',
    'UIA_ScrollHorizontallyScrollablePropertyId',
    'UIA_IsTablePatternAvailablePropertyId',
    'IUIAutomationObjectModelPattern', 'StyleId_BulletedList',
    'UIA_IsInvokePatternAvailablePropertyId',
    'TextEditChangeType_CompositionFinalized',
    'UIA_HeaderControlTypeId', 'AutomationElementMode_Full',
    'HeadingLevel5', 'UIA_LiveRegionChangedEventId',
    'AnnotationType_DataValidationError',
    'UIA_RangeValueLargeChangePropertyId',
    'TreeTraversalOptions_PostOrder',
    'UIA_IsRangeValuePatternAvailablePropertyId',
    'UIA_SelectionIsSelectionRequiredPropertyId',
    'UIA_SpreadsheetItemAnnotationTypesPropertyId',
    'UIA_WindowWindowInteractionStatePropertyId',
    'OrientationType_Vertical', 'UIA_FontWeightAttributeId',
    'AnnotationType_TrackChanges',
    'UIA_DropTargetDropTargetEffectsPropertyId',
    'UIA_StylesFillColorPropertyId', 'IUIAutomationTextRange2',
    'UIA_SelectionPatternId',
    'UIA_IsSynchronizedInputPatternAvailablePropertyId',
    'IUIAutomation2', 'Off', 'UIA_AnnotationTypesAttributeId',
    'WindowInteractionState_NotResponding',
    'WindowVisualState_Maximized', 'WindowInteractionState_Running',
    'UIA_IsSelectionPattern2AvailablePropertyId',
    'UIA_IsGridItemPatternAvailablePropertyId',
    'UIA_TransformCanMovePropertyId',
    'NavigateDirection_PreviousSibling', 'UIA_AnnotationPatternId',
    'UIA_AnnotationTypesPropertyId', 'UIA_ListItemControlTypeId',
    'TextPatternRangeEndpoint', 'UIA_SemanticZoomControlTypeId',
    'UIA_AnnotationAnnotationTypeNamePropertyId',
    'ExpandCollapseState', 'AnnotationType_ExternalChange',
    'UIA_StyleIdAttributeId', 'UIA_AutomationIdPropertyId',
    'AnnotationType_CircularReferenceError',
    'OrientationType_Horizontal', 'UIA_TextPatternId',
    'NotificationProcessing', 'UIA_ItemContainerPatternId',
    'TextUnit_Page', 'IUIAutomationTogglePattern',
    'UIA_StatusBarControlTypeId', 'UIA_Selection_InvalidatedEventId',
    'UIA_IsTextChildPatternAvailablePropertyId', 'ProviderOptions',
    'UIA_IsSelectionPatternAvailablePropertyId',
    'IUIAutomationElement', 'HeadingLevel9', 'UIA_SizePropertyId',
    'DockPosition_Left', 'PropertyConditionFlags_IgnoreCase',
    'AnnotationType_Header', 'UIA_TableControlTypeId',
    'TreeScope_Children', 'IUIAutomation3', 'AnnotationType_Footnote',
    'HeadingLevel1', 'UIA_IsReadOnlyAttributeId',
    'RowOrColumnMajor_RowMajor', 'UIA_TogglePatternId',
    'UIA_EditControlTypeId', 'UIA_RangeValuePatternId',
    'StyleId_Subtitle',
    'UIA_LegacyIAccessibleKeyboardShortcutPropertyId',
    'UIA_HasKeyboardFocusPropertyId', 'UIA_ItemStatusPropertyId',
    'UIA_ObjectModelPatternId', 'RowOrColumnMajor_Indeterminate',
    'UIA_AutomationPropertyChangedEventId', 'IUIAutomation5',
    'AnnotationType_Endnote',
    'UIA_TextEdit_ConversionTargetChangedEventId',
    'UIA_AnnotationObjectsAttributeId', 'UIA_DropTargetPatternId',
    'UIA_TableItemPatternId', 'SupportedTextSelection_Multiple',
    'UIA_IsWindowPatternAvailablePropertyId',
    'SynchronizedInputType_KeyUp', 'TextUnit_Character',
    'ZoomUnit_NoAmount', 'UIA_WindowPatternId',
    'IUIAutomationSelectionItemPattern', 'Assertive',
    'TreeTraversalOptions_Default',
    'UIA_LegacyIAccessibleRolePropertyId',
    'UIA_TableColumnHeadersPropertyId',
    'CoalesceEventsOptions_Enabled', 'AnnotationType_FormatChange',
    'UIA_RuntimeIdPropertyId', 'ToggleState_Indeterminate',
    'IUIAutomationPropertyCondition', 'AutomationElementMode_None',
    'typelib_path', 'TreeScope_Element', 'UIA_FillColorPropertyId',
    'UIA_ScrollItemPatternId', 'UIA_IsGridPatternAvailablePropertyId',
    'UIA_SpreadsheetItemPatternId', 'IUIAutomationTextPattern2',
    'UIA_IsValuePatternAvailablePropertyId',
    'UIA_DropTarget_DragLeaveEventId', 'NavigateDirection_LastChild',
    'UIA_ProgressBarControlTypeId',
    'PropertyConditionFlags_MatchSubstring', 'StyleId_NumberedList',
    'IUIAutomationElement2', 'IUIAutomation',
    'UIA_ToolTipClosedEventId',
    'UIA_IsTransformPatternAvailablePropertyId',
    'UIA_ItemTypePropertyId', 'WindowInteractionState_Closing',
    'UIA_HelpTextPropertyId', 'UIA_IsOffscreenPropertyId',
    'UIA_SelectionPattern2Id',
    'UIA_BeforeParagraphSpacingAttributeId', 'UIA_LinkAttributeId',
    'WindowVisualState_Minimized',
    'ProviderOptions_HasNativeIAccessible',
    'IUIAutomationSelectionPattern2', 'UIA_SplitButtonControlTypeId',
    'IUIAutomationElement4', 'IUIAutomationCacheRequest',
    'ZoomUnit_SmallIncrement',
    'UIA_IsDropTargetPatternAvailablePropertyId',
    'AnnotationType_Footer', 'IUIAutomationTransformPattern',
    'UIA_IndentationFirstLineAttributeId',
    'UIA_Text_TextChangedEventId',
    'UIA_IsScrollItemPatternAvailablePropertyId',
    'UIA_IsHiddenAttributeId', 'IUIAutomationInvokePattern',
    'AnnotationType_UnsyncedChange', 'UIA_IsItalicAttributeId',
    'UIA_ClickablePointPropertyId', 'UIA_WindowIsModalPropertyId',
    'StyleId_Heading2', 'UIA_SizeOfSetPropertyId',
    'TextEditChangeType_AutoComplete', 'UIA_GridItemRowPropertyId',
    'UIA_IsItemContainerPatternAvailablePropertyId',
    'UIA_IsLegacyIAccessiblePatternAvailablePropertyId',
    'NotificationProcessing_All', 'UIA_SynchronizedInputPatternId',
    'IUIAutomationItemContainerPattern', 'UIA_FontSizeAttributeId',
    'UIA_Selection2CurrentSelectedItemPropertyId',
    'ProviderOptions_NonClientAreaProvider',
    'UIA_IsTransformPattern2AvailablePropertyId',
    'UIA_SelectionItem_ElementAddedToSelectionEventId',
    'IUIAutomationValuePattern', 'NotificationKind_ItemRemoved',
    'UIA_CapStyleAttributeId', 'UIA_DragGrabbedItemsPropertyId',
    'ProviderOptions_ClientSideProvider', 'UIA_IsPasswordPropertyId',
    'UIA_IsTextEditPatternAvailablePropertyId',
    'IUIAutomationSpreadsheetPattern',
    'UIA_AnimationStyleAttributeId', 'TextUnit_Document',
    'ToggleState_Off', 'UIA_ActiveTextPositionChangedEventId',
    'UIA_StylesStyleIdPropertyId', 'UIA_LandmarkTypePropertyId',
    'SynchronizedInputType_RightMouseUp', 'UIA_ThumbControlTypeId',
    'UIA_AppBarControlTypeId',
    'UIA_IsTableItemPatternAvailablePropertyId',
    'ZoomUnit_LargeDecrement',
    'UIA_SelectionItemIsSelectedPropertyId',
    'UIA_Selection2FirstSelectedItemPropertyId',
    'ExpandCollapseState_PartiallyExpanded',
    'UIA_SearchLandmarkTypeId', 'UIA_PositionInSetPropertyId',
    'IUIAutomationNotCondition', 'UIA_CustomLandmarkTypeId',
    'StyleId_Custom',
    'UIA_IsExpandCollapsePatternAvailablePropertyId',
    'UIA_WindowControlTypeId', 'UIA_RotationPropertyId',
    'TreeScope_None', 'UIA_MenuOpenedEventId',
    'UIA_IsEnabledPropertyId', 'HeadingLevel4',
    'UIA_CultureAttributeId', 'IUIAutomationGridItemPattern',
    'UIA_AriaPropertiesPropertyId', 'ProviderOptions_UseComThreading',
    'NavigateDirection_FirstChild', 'IUIAutomationScrollItemPattern',
    'UIA_StructureChangedEventId', 'TreeScope_Ancestors',
    'UIA_StylesExtendedPropertiesPropertyId',
    'UIA_VirtualizedItemPatternId', 'UIA_LevelPropertyId',
    'StructureChangeType_ChildRemoved',
    'SynchronizedInputType_RightMouseDown',
    'TextEditChangeType_Composition',
    'UIA_ScrollVerticalViewSizePropertyId',
    'UIA_WindowWindowVisualStatePropertyId', 'StyleId_Quote',
    'Library', 'UIA_SelectionItem_ElementRemovedFromSelectionEventId',
    'UIA_IsDialogPropertyId', 'UIA_PaneControlTypeId',
    'UIA_IsDataValidForFormPropertyId', 'TextUnit_Format',
    'UIA_IsControlElementPropertyId',
    'UIA_OutlineThicknessPropertyId', 'AnnotationType_Highlighted',
    'UIA_InputDiscardedEventId',
    'UIA_LocalizedLandmarkTypePropertyId',
    'UIA_CenterPointPropertyId', 'IUIAutomationScrollPattern',
    'UIA_ScrollBarControlTypeId', 'ZoomUnit_SmallDecrement',
    'UIA_MarginLeadingAttributeId', 'TextUnit',
    'UIA_ToggleToggleStatePropertyId', 'IUIAutomation6',
    'UIA_DragIsGrabbedPropertyId',
    'UIA_LegacyIAccessibleNamePropertyId', 'UIA_AccessKeyPropertyId',
    'IUIAutomationElement8', 'AnnotationType_Unknown',
    'UIA_FontNameAttributeId', 'UIA_StylesFillPatternStylePropertyId',
    'UIA_IsKeyboardFocusablePropertyId', 'IUIAutomationCondition',
    'SupportedTextSelection_None', 'SynchronizedInputType',
    'UIA_LegacyIAccessibleSelectionPropertyId',
    'IUIAutomationTextChildPattern', 'AnnotationType_SpellingError',
    'UIA_ControlTypePropertyId', 'UIA_StylesStyleNamePropertyId',
    'UIA_ToolTipOpenedEventId', 'IRawElementProviderSimple',
    'UIA_TextEditPatternId', 'UIA_SayAsInterpretAsAttributeId',
    'UIA_UnderlineStyleAttributeId', 'DockPosition_Fill',
    'ProviderOptions_RefuseNonClientSupport', 'UIA_FlowsToPropertyId',
    'UIA_OutlineStylesAttributeId',
    'ProviderOptions_ServerSideProvider',
    'UIA_IsContentElementPropertyId', 'AnnotationType_Mathematics',
    'UIA_TransformPatternId', 'UIA_BulletStyleAttributeId',
    'UIA_TransformCanResizePropertyId', 'UIA_TreeItemControlTypeId',
    'StyleId_Heading8', 'UIA_ScrollHorizontalScrollPercentPropertyId',
    'UIA_MainLandmarkTypeId', 'LiveSetting',
    'AnnotationType_EditingLockedChange',
    'StructureChangeType_ChildAdded', 'ZoomUnit_LargeIncrement',
    'NotificationKind_ActionAborted', 'UIA_Drag_DragCompleteEventId',
    'UIA_AnnotationAnnotationTypeIdPropertyId',
    'UIA_TextFlowDirectionsAttributeId', 'UIA_DockPatternId',
    'IUIAutomationTextEditTextChangedEventHandler',
    'IUIAutomationNotificationEventHandler', 'IUIAutomationElement9',
    'UIA_IsTogglePatternAvailablePropertyId',
    'UIA_MarginTrailingAttributeId',
    'UIA_WindowCanMinimizePropertyId',
    'UIA_ExpandCollapseExpandCollapseStatePropertyId',
    'UIA_OverlineColorAttributeId',
    'IUIAutomationLegacyIAccessiblePattern', 'ScrollAmount_NoAmount',
    'IUIAutomationVirtualizedItemPattern', 'DockPosition_Bottom',
    'WindowInteractionState', 'UIA_DropTarget_DragEnterEventId',
    'UIA_TreeControlTypeId', 'UIA_SelectionActiveEndAttributeId',
    'UIA_IsVirtualizedItemPatternAvailablePropertyId',
    'UIA_RangeValueIsReadOnlyPropertyId', 'AnnotationType_Comment',
    'IUIAutomationTransformPattern2',
    'StructureChangeType_ChildrenBulkAdded', 'HeadingLevel2',
    'ScrollAmount_LargeDecrement',
    'UIA_DropTargetDropTargetEffectPropertyId',
    'UIA_IsScrollPatternAvailablePropertyId', 'RowOrColumnMajor',
    'TextEditChangeType_AutoCorrect',
    'IUIAutomationActiveTextPositionChangedEventHandler',
    'UIA_AnnotationObjectsPropertyId',
    'UIA_IsDockPatternAvailablePropertyId', 'UIA_FillTypePropertyId',
    'UIA_IsSuperscriptAttributeId',
    'IUIAutomationMultipleViewPattern',
    'StructureChangeType_ChildrenBulkRemoved'
]

