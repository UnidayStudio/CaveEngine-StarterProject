import cave
import cave.event
import cave.math

class Player(cave.Component):
	def start(self, scene: cave.Scene):
		self.walkSpeed = 0.025
		self.runSpeed = 0.075

		self.transf = self.entity.getTransform()
		self.character : cave.CharacterComponent = self.entity.get("Character")

		self.mesh = self.entity.getChild("Mesh")
		self.meshTransf = self.mesh.getTransform()
		self.animator : cave.AnimationComponent = self.mesh.get("Animation")

		# To control the Health:
		self.lifeBar = self.entity.getChild("LifeBar")
		self.lifeBarUI : cave.UIElementComponent = self.lifeBar.get("UIElement")

		# For the Ground IK:
		self.animator.addPostEvaluationCallback(self.postEvaluation)
		self._ikBlend = {}

	def postEvaluation(self):
		# This method will create the Inverse Kinematic for the Character's foot

		dt = cave.getDeltaTime()
		arm : cave.Armature = self.animator.armature.get()
		scene = self.entity.getScene()

		# Replace those 3 bone names with your own Foot and Hip bones:
		hips = arm.getBone("mixamorig:Hips")
		boneL = arm.getBone("mixamorig:LeftFoot")
		boneR = arm.getBone("mixamorig:RightFoot")

		def evaluateIK(bone : cave.Bone):
			worldPos = self.meshTransf.transformVector(bone.getWorldPosition())
			worldPos.y = self.transf.worldPosition.y

			mask = cave.BitMask(False)
			mask.enable(7)
			
			dir = cave.Vector3(0, 1, 0)
			res = scene.rayCast(worldPos + dir * 0.5, worldPos - dir * 0.6, mask)

			out = res.position.y - worldPos.y if res.hit else 0
			self._ikBlend[bone.name] = cave.math.lerp(self._ikBlend.get(bone.name, out), out, 6 * dt)
			return self._ikBlend[bone.name]

		resL = evaluateIK(boneL)
		resR = evaluateIK(boneR)

		offset = min(resL, resR)

		posL = boneL.worldPosition + cave.Vector3(0, resL, 0)
		posR = boneR.worldPosition + cave.Vector3(0, resR, 0)

		hips.setWorldPosition(hips.getWorldPosition() + cave.Vector3(0, offset, 0))

		boneL.twoPartIK(posL)
		boneR.twoPartIK(posR)

	def update(self):
		dt = cave.getDeltaTime()
		scene = self.entity.getScene()
		events = cave.getEvents()

		# Jumping:
		if self.character.onGround() and events.pressed(cave.event.KEY_SPACE):
			self.character.jump()

		# Movements:
		z = events.active(cave.event.KEY_W) - events.active(cave.event.KEY_S)
		x = events.active(cave.event.KEY_A) - events.active(cave.event.KEY_D)
		dir = cave.Vector3(x, 0, z)

		isMoving = dir.length() > 0
		if isMoving:
			dir.normalize()
			self.meshTransf.lookAtSmooth(self.transf.transformDirection(-dir), 6.0 * dt)

		isRunning = events.active(cave.event.KEY_LSHIFT)
		speed = self.runSpeed if isRunning else self.walkSpeed

		# Applying the Movement:
		self.character.setWalkDirection(dir * speed)

		# Calculating the Animations:
		if self.character.onGround():
			if isMoving:
				if isRunning:
					self.animator.playByName("p-run", blend=0.2, loop=True)
				else:
					self.animator.playByName("p-walk", blend=0.2, loop=True)
			else:
				self.animator.playByName("p-idle", blend=0.2, loop=True)
		else:
			self.animator.playByName("p-fall", blend=0.2, loop=True)

		# Updating the Health:
		if events.active(cave.event.KEY_C):
			self.entity.properties["health"] -= 1
		if events.active(cave.event.KEY_V):
			self.entity.properties["health"] += 1
		
		# Clamping and Displaying the Health in the UI:
		self.entity.properties["health"] = cave.math.clamp(self.entity.properties["health"], 0, 100)
		self.lifeBarUI.scale.setRelativeX(self.entity.properties["health"] / 100)

		# Game Over...
		if self.entity.properties["health"] <= 0:
			self.entity.getChild("Game Over").activate(scene)

		# Next Level...
		next = self.character.getCollisionsWith("portal")
		if len(next) > 0:
			self.entity.properties["portal"] = next[0].entity.properties["scene"]
			self.entity.getChild("Level Complete").activate(scene)

		
	def end(self, scene: cave.Scene):
		pass
	