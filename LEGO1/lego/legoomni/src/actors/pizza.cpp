#include "pizza.h"

#include "isle.h"
#include "isle_actions.h"
#include "legoanimationmanager.h"
#include "legogamestate.h"
#include "legoworld.h"
#include "misc.h"
#include "mxmisc.h"
#include "mxticklemanager.h"

DECOMP_SIZE_ASSERT(Pizza, 0x9c)
DECOMP_SIZE_ASSERT(PizzaMissionState, 0xb4)
DECOMP_SIZE_ASSERT(PizzaMissionState::Entry, 0x20)

// Flags used in isle.cpp
extern MxU32 g_isleFlags;

// FUNCTION: LEGO1 0x10037ef0
Pizza::Pizza()
{
	m_state = NULL;
	m_entry = NULL;
	m_skateboard = NULL;
	m_act1state = NULL;
	m_unk0x8c = -1;
	m_unk0x98 = 0;
	m_unk0x90 = 0x80000000;
}

// FUNCTION: LEGO1 0x10038100
Pizza::~Pizza()
{
	TickleManager()->UnregisterClient(this);
}

// FUNCTION: LEGO1 0x10038170
MxResult Pizza::Create(MxDSAction& p_dsAction)
{
	MxResult result = IsleActor::Create(p_dsAction);

	if (result == SUCCESS) {
		CreateState();
		m_skateboard = (SkateBoard*) m_world->Find(m_atomId, IsleScript::c_SkateBoard_Actor);
	}

	return result;
}

// FUNCTION: LEGO1 0x100381b0
void Pizza::CreateState()
{
	m_state = (PizzaMissionState*) GameState()->GetState("PizzaMissionState");
	if (m_state == NULL) {
		m_state = (PizzaMissionState*) GameState()->CreateState("PizzaMissionState");
	}

	m_act1state = (Act1State*) GameState()->GetState("Act1State");
	if (m_act1state == NULL) {
		m_act1state = (Act1State*) GameState()->CreateState("Act1State");
	}
}

// FUNCTION: LEGO1 0x10038220
void Pizza::FUN_10038220(MxU32 p_objectId)
{
	AnimationManager()->FUN_10064740(NULL);
	m_entry = m_state->GetState(GameState()->GetActorId());
	m_state->m_unk0x0c = 1;
	m_act1state->m_unk0x018 = 3;
	m_entry->m_unk0x10 = 0x80000000;
	g_isleFlags &= ~Isle::c_playMusic;
	AnimationManager()->EnableCamAnims(FALSE);
	AnimationManager()->FUN_1005f6d0(FALSE);
	FUN_10038fe0(p_objectId, FALSE);
	m_unk0x8c = -1;
}

// STUB: LEGO1 0x100382b0
void Pizza::FUN_100382b0()
{
}

// STUB: LEGO1 0x10038380
void Pizza::FUN_10038380()
{
}

// STUB: LEGO1 0x100383f0
MxLong Pizza::HandleClick()
{
	// TODO
	return 0;
}

// STUB: LEGO1 0x100384f0
MxLong Pizza::HandlePathStruct(LegoPathStructNotificationParam&)
{
	// TODO
	return 0;
}

// STUB: LEGO1 0x100388a0
MxResult Pizza::Tickle()
{
	// TODO
	return SUCCESS;
}

// STUB: LEGO1 0x10038b10
MxLong Pizza::HandleEndAction(MxEndActionNotificationParam&)
{
	// TODO
	return 0;
}

// STUB: LEGO1 0x10038fe0
void Pizza::FUN_10038fe0(MxU32 p_objectId, MxBool)
{
	// TODO
}

// STUB: LEGO1 0x10039030
PizzaMissionState::PizzaMissionState()
{
	// TODO
}

// FUNCTION: LEGO1 0x100393c0
MxResult PizzaMissionState::Serialize(LegoFile* p_file)
{
	LegoState::Serialize(p_file);

	if (p_file->IsReadMode()) {
		for (MxS16 i = 0; i < 5; i++) {
			m_state[i].ReadFromFile(p_file);
		}
	}
	else if (p_file->IsWriteMode()) {
		for (MxS16 i = 0; i < 5; i++) {
			m_state[i].WriteToFile(p_file);
		}
	}

	return SUCCESS;
}

// FUNCTION: LEGO1 0x10039510
PizzaMissionState::Entry* PizzaMissionState::GetState(MxU8 p_id)
{
	for (MxS16 i = 0; i < 5; i++) {
		if (m_state[i].m_id == p_id) {
			return m_state + i;
		}
	}

	return NULL;
}
