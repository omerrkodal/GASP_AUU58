// Copyright GASP_AUU58. All Rights Reserved.
#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintAsyncActionBase.h"
#include "Engine/StreamableManager.h"
#include "Engine/AssetManager.h"
#include "AsyncAction_LoadDataAsset.generated.h"

DECLARE_DYNAMIC_MULTICAST_DELEGATE(FOnDataAssetLoaded);

/**
 * Async node: walks every property on a Data Asset (including inside structs and
 * maps), collects ALL TSoftObjectPtr / TSoftClassPtr references, and batch-loads
 * them. Fires OnLoaded when every soft ref is resident in memory.
 *
 * After OnLoaded fires, you can access any field on the Data Asset normally —
 * soft refs can be resolved with .Get() or the Blueprint "Get" accessors.
 *
 * Blueprint usage:
 *   [Get Weapon Data Asset] → [Async Load Data Asset] → OnLoaded
 *   → [Get Weapon Data Asset → SwapAnimations → Find "RightShoulder" → AnimMontage.Get()]
 *
 * Works with any nesting depth: Map<Enum, Struct{ Soft<Montage> }> is handled.
 */
UCLASS(meta=(HideThen=true))
class ASSETLOADER_API UAsyncAction_LoadDataAsset : public UBlueprintAsyncActionBase
{
	GENERATED_BODY()

public:

	/** Fires once when ALL soft references inside the Data Asset are loaded. */
	UPROPERTY(BlueprintAssignable)
	FOnDataAssetLoaded OnLoaded;

	/** Fires if no soft references were found, or all paths were null. */
	UPROPERTY(BlueprintAssignable)
	FOnDataAssetLoaded OnFailed;

	/**
	 * Walks the entire Data Asset (and nested structs) and async-loads every
	 * soft object/class reference found.
	 *
	 * @param DataAsset      Any UObject — your weapon Data Asset, config asset, etc.
	 * @param bHighPriority  True = load now (equipping weapon). False = background preload.
	 */
	UFUNCTION(BlueprintCallable, Category="AssetLoader",
	          meta=(BlueprintInternalUseOnly="true", WorldContext="WorldContextObject",
	                DisplayName="Async Load Data Asset (All Soft Refs)",
	                ToolTip="Loads every soft reference inside the Data Asset. After OnLoaded fires, all soft refs are safe to use."))
	static UAsyncAction_LoadDataAsset* AsyncLoadDataAsset(
		UObject* WorldContextObject,
		UObject* DataAsset,
		bool bHighPriority = true);

	virtual void Activate() override;

private:
	void OnLoadComplete();

	/** Recursively collects all FSoftObjectPath from a UObject's properties, including inside structs and maps. */
	static void CollectPathsFromObject(UObject* Object, TArray<FSoftObjectPath>& OutPaths);

	/** Recursively collects soft paths from a struct value pointer. */
	static void CollectPathsFromStruct(const void* StructData, const UStruct* Struct, TArray<FSoftObjectPath>& OutPaths);

	UPROPERTY()
	TObjectPtr<UObject> WorldContext;

	UPROPERTY()
	TObjectPtr<UObject> TargetDataAsset;

	bool bHighPriority = true;

	TSharedPtr<FStreamableHandle> Handle;
};
