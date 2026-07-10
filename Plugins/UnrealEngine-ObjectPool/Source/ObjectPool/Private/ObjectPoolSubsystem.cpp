#include "ObjectPoolSubsystem.h"
#include "ObjectPooledActorInterface.h"
#include "ObjectPoolSettings.h"
#include "Kismet/GameplayStatics.h"

DECLARE_LOG_CATEGORY_CLASS(LogObjectPool, Display, All);

UObjectPool::UObjectPool()
{
}

bool UObjectPool::DoesSupportWorldType(const EWorldType::Type WorldType) const
{
	switch (WorldType)
	{
	case EWorldType::None:
		return false;
	case EWorldType::Game:
		return true;
	case EWorldType::Editor:
		return false;
	case EWorldType::PIE:
		return true;
	case EWorldType::EditorPreview:
		return false;
	case EWorldType::GamePreview:
		return true;
	case EWorldType::GameRPC:
		return true;
	case EWorldType::Inactive:
		return false;
	}

	return Super::DoesSupportWorldType(WorldType);
}

void UObjectPool::OnWorldBeginPlay(UWorld& InWorld)
{
	Super::OnWorldBeginPlay(InWorld);

	const UObjectPoolSettings* Settings = GetDefault<UObjectPoolSettings>();

	for (TTuple<TSubclassOf<AActor>, FPooledActorSettings> Element : Settings->InitialActorsToPool)
	{
		if (!AddActorType(Element.Key, Element.Value))
		{
			UE_LOG(LogObjectPool, Error, TEXT("Failed to spawn initial count of actor class \"%s\""),
			       IsValid(Element.Key) ? *Element.Key->GetDisplayNameText().ToString() : *FString("Unknown class"))
		}
	}
}

void UObjectPool::Deinitialize()
{
	const UObjectPoolSettings* Settings = GetDefault<UObjectPoolSettings>();

	if (!Settings || !Settings->bDestroyOnEndPlay)
	{
		return;
	}

	for (auto& Element : Pool)
	{
		for (TWeakObjectPtr<AActor>& ActivePoolActor : Element.Value.Key)
		{
			if (ActivePoolActor.IsValid())
			{
				ActivePoolActor->Destroy();
			}
		}

		for (TWeakObjectPtr<AActor>& InactivePoolActor : Element.Value.Value)
		{
			if (InactivePoolActor.IsValid())
			{
				InactivePoolActor->Destroy();
			}
		}
	}

	Super::Deinitialize();
}

bool UObjectPool::Push(AActor* Actor)
{
	if (IsValid(Actor))
	{
		if (Actor->GetClass()->ImplementsInterface(UObjectPooledActor::StaticClass()))
		{
			if (!Pool.Contains(Actor->GetClass()))
			{
				if (!AddActorType(Actor->GetClass(), FPooledActorSettings(0, true)))
				{
					UE_LOG(LogObjectPool, Error, TEXT("Pushed actor of type \"%s\" did not already exist in pool and could not be added either"),
					       *Actor->GetClass()->GetDisplayNameText().ToString())
					return false;
				}

				if (!Pool.Contains(Actor->GetClass()))
				{
					return false;
				}
			}

			TTuple<TArray<TWeakObjectPtr<AActor>>, TArray<TWeakObjectPtr<AActor>>>* Subpools = Pool.Find(Actor->GetClass());
			Subpools->Key.RemoveSwap(Actor);   // O(1): swap-with-last, no array shift
			Subpools->Value.Add(Actor);         // O(1): pool guarantees no duplicates
			IObjectPooledActor::Execute_OnPushedToPool(Actor);
			return true;
		}
	}

	return false;
}

bool UObjectPool::Pull(const TSubclassOf<AActor> Class, AActor*& Actor_Out)
{
	TTuple<TArray<TWeakObjectPtr<AActor>>, TArray<TWeakObjectPtr<AActor>>>* Subpool = Pool.Find(Class);
	if (!Subpool)
	{
		if (!AddActorType(Class, FPooledActorSettings(0, true)))
		{
			UE_LOG(LogObjectPool, Error, TEXT("Pulled actor type \"%s\" did not already exist in pool and could not be added either"), *Class->GetDisplayNameText().ToString())
			return false;
		}

		Subpool = Pool.Find(Class);
		if (!Subpool)
		{
			UE_LOG(LogObjectPool, Error, TEXT("Could not find subpool even after adding actor type"))
			return false;
		}
	}

	AActor* PulledActor = nullptr;

	// inactive pool
	for (int32 Index = 0; Index < Subpool->Value.Num(); ++Index)
	{
		if (Subpool->Value[Index].IsValid())
		{
			PulledActor = Subpool->Value[Index].Get();
			Actor_Out = PulledActor;
			Subpool->Value.RemoveAtSwap(Index); // O(1): swap-with-last, no array shift
			break;
		}
	}

	if (IsValid(PulledActor))
	{
		Subpool->Key.Add(PulledActor);         // O(1): pool guarantees no duplicates
		IObjectPooledActor::Execute_OnPulledFromPool(PulledActor);
		Actor_Out = PulledActor;
		return true;
	} else
	{
		FPooledActorSettings* Settings = ActivePoolSettings.Find(Class);
		if (Settings && Settings->bCanExpand)
		{
			PulledActor = SpawnNewActor(Class);
			if (!IsValid(PulledActor))
			{
				return false;
			}
			Subpool->Key.Add(PulledActor);         // O(1): pool guarantees no duplicates
			IObjectPooledActor::Execute_OnPulledFromPool(PulledActor);
			Actor_Out = PulledActor;
			return true;
		}
		else if (Subpool->Key.Num() > 0)
		{
			// Pool is full and cannot expand. Implement FIFO by recycling the oldest active actor.
			PulledActor = Subpool->Key[0].Get();
			if (IsValid(PulledActor))
			{
				Push(PulledActor); // Pushes to inactive pool, triggering OnPushedToPool (cleanup/hide)
				
				// Now it's the last added in the inactive pool (Value), grab it
				if (Subpool->Value.Num() > 0)
				{
					PulledActor = Subpool->Value.Last().Get();
					Actor_Out = PulledActor;
					Subpool->Value.RemoveAtSwap(Subpool->Value.Num() - 1); // O(1): last element, swap is no-op
					Subpool->Key.Add(PulledActor);         // O(1): pool guarantees no duplicates
					IObjectPooledActor::Execute_OnPulledFromPool(PulledActor); // Re-activate
					return true;
				}
			}
		}

		return false;
	}
}

AActor* UObjectPool::SpawnNewActor(const TSubclassOf<AActor>& Class) const
{
	if (UWorld* World = this->GetWorld(); World != nullptr)
	{
		FActorSpawnParameters Params;
		Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
		AActor* NewActor = World->SpawnActor<AActor>(Class.Get(), FVector(0, 0, 0), FRotator(0, 0, 0), Params);
		if (!IsValid(NewActor))
		{
			UE_LOG(LogObjectPool, Error, TEXT("Failed to spawn actor of class \"%s\""), *Class->GetDisplayNameText().ToString())
			return nullptr;
		}

		return NewActor;
	}
	return nullptr;
}

bool UObjectPool::AddActorType(TSubclassOf<AActor> Class, FPooledActorSettings ActorSettings)
{
	if (IsValid(Class))
	{
		if (!UKismetSystemLibrary::DoesClassImplementInterface(Class, UObjectPooledActor::StaticClass()))
		{
			UE_LOG(LogObjectPool, Error, TEXT("The actor class \"%s\" does not implement the \"%s\" interface"), *Class->GetDisplayNameText().ToString(),
			       *UObjectPooledActor::StaticClass()->GetDisplayNameText().ToString())
			return false;
		}

		if (!Pool.Contains(Class))
		{
			TArray<TWeakObjectPtr<AActor>> InactivePool;

			ActivePoolSettings.Add(Class, ActorSettings);

			for (int i = 0; i < ActorSettings.InitialSpawnCount; ++i)
			{
				AActor* NewActor = SpawnNewActor(Class);
				if (!IsValid(NewActor))
				{
					UE_LOG(LogObjectPool, Error, TEXT("AddActorType() failed to spawn new actor"))
					continue;
				}
				InactivePool.AddUnique(NewActor);
				IObjectPooledActor::Execute_OnPushedToPool(NewActor);
			}

			Pool.Add(Class, TTuple<TArray<TWeakObjectPtr<AActor>>, TArray<TWeakObjectPtr<AActor>>>(TArray<TWeakObjectPtr<AActor>>(), InactivePool));
			return true;
		}
	}

	return false;
}
