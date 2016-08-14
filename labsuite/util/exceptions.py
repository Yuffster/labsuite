class ProtocolException(Exception):
	"""
	A user-level Exception thrown when a Protocol is improperly defined.

	These are designed to provide information to the user on how to 
	resolve specific issues in the definition or operation of a 
	Protocol.
	"""

class MissingData(ProtocolException):
	"""
	Thrown when not enough data is provided either by the user or the
	context to complete a call.
	"""

class ProtocolConflict(ProtocolException):
	"""
	Raised when a Protocol definition conflicts with another in the same
	Protocol, such as reuse of a label or slot position for two different
	containers, or multiple instruments assigned to the same axis.
	"""

class ContainerConflict(ProtocolConflict):
	"""
	Raised when a container is already allocated to a particular slot,
	or uses the same label.
	"""

class InstrumentConflict(ProtocolConflict):
	"""
	Raised when an instrument can't be placed in a particular axis because the
	desired axis is already in use.
	"""

class ProtocolMissingItem(ProtocolException):
	"""
	Raised when an element is missing from a Protocol, such as when a
	transfer references a container that doesn't exist.
	"""

class MissingInstrument(ProtocolMissingItem):
	"""
	Raised when an instrument an indicated instrument does not exist, or when
	no instrument can be found to complete a particular task.
	"""

class MissingContainer(ProtocolMissingItem):
	"""
	Raised when an indicated container does not exist in a Protocol.
	"""

class MissingTip(ProtocolMissingItem):
	"""
	Thrown when no available tip can be found to attach to a particular
	pipette.
	"""

class MissingCommand(ProtocolMissingItem):
	"""
	Thrown when a desired command is unavailable.
	"""

class VolumeException(ProtocolException):
	"""
	Thrown when something is wrong with the volume designated in a transfer,
	either that the source well does not contain the requisite amount or when
	the destination will be overflowed by a transfer.
	"""

class VolumeOverflow(VolumeException):
	"""
	Thrown when the volume to be transferred to a destination exceeds the
	maximum capacity of a well.
	"""

class VolumeUnavailable(VolumeException):
	"""
	Thrown when the volume to be transferred does not exist or is
	insufficient.
	"""

class VolumeMismatch(VolumeException):
	"""
	Thrown when the volume specified is of a different type than what is
	available in a particular container.
	"""
