#ifndef HELICOPTER_H
#define HELICOPTER_H

#include "islepathactor.h"
#include "realtime/matrix.h"

class HelicopterState;

// VTABLE: LEGO1 0x100d40f8
// SIZE 0x230
class Helicopter : public IslePathActor {
public:
	Helicopter();
	~Helicopter() override; // vtable+0x00

	// FUNCTION: LEGO1 0x10003070
	inline const char* ClassName() const override // vtable+0x0c
	{
		// STRING: LEGO1 0x100f0130
		return "Helicopter";
	}

	// FUNCTION: LEGO1 0x10003080
	inline MxBool IsA(const char* p_name) const override // vtable+0x10
	{
		return !strcmp(p_name, Helicopter::ClassName()) || IslePathActor::IsA(p_name);
	}

	MxResult Create(MxDSAction& p_dsAction) override;                 // vtable+0x18
	void VTable0x70(float p_float) override;                          // vtable+0x70
	void VTable0x74(Matrix4& p_transform) override;                   // vtable+0x74
	MxU32 VTable0xcc() override;                                      // vtable+0xcc
	MxU32 VTable0xd4(LegoControlManagerEvent& p_param) override;      // vtable+0xd4
	MxU32 VTable0xd8(LegoEndAnimNotificationParam& p_param) override; // vtable+0xd8
	void VTable0xe4() override;                                       // vtable+0xe4

	// SYNTHETIC: LEGO1 0x10003210
	// Helicopter::`scalar deleting destructor'

	void CreateState();

protected:
	MxMatrix m_unk0x160;              // 0x160
	MxMatrix m_unk0x1a8;              // 0x1a8
	float m_unk0x1f0;                 // 0x1f0
	UnknownMx4DPointFloat m_unk0x1f4; // 0x1f4
	HelicopterState* m_state;         // 0x228
	MxAtomId m_script;                // 0x22c
};

#endif // HELICOPTER_H
