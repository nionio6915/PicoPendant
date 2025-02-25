# Jog Screen
# --------------------------
from network import WLAN, STA_IF
import ujson as json
import web.arequest as arequest
from utime import ticks_ms, ticks_diff, ticks_add
from display.colorSet import SolidClr
from display.ioBox import IoBox
from screens.screen import pp_screen
from util.picoPendant import GlobalPico
from display.lcdDriver import GlobalLcd
from web.wifiConnect import doConnect
import uasyncio as asyncio
import gc

# show X,Y,Z position, let an encoder move left/right
# touch-screen for x-y-z or switch ? or 2 encoders for x,y
# to get position from RRF use  http:/rrf/rr_status and get a stream back with machine and pos

def RunJogger() :
	''' run the thing. if you do x = RunJogger() then you can use x.Loop() to rerun it '''
	didi = False
	try :
		x=JogScreen()
		x.Setup()
		asyncio.run( x.Loop())
	except Exception as e:
		print('failure ' + str(e))
	return x

class JogScreen(pp_screen) :

	def __init__(self) :
		self.Xtext = None
		self.Ytext = None
		self.Ztext = None
		self.Xmtext = None
		self.Ymtext = None
		self.Zmtext = None
		self.Locn = [0,0,0] # location in user coords
		self.Mach = [0,0,0] # location in machine coords
		self.lspace = 4
		self.indent = 10
		self.yTitle = 10
		self.dialEdit = 'T'	# tic size
		self.showMachine = False
		self.Brightness = 70
		self.LastTouch = [0,0,0,0,0]
		self.isTouchDown = False
		self.WhenTouch = 0
		self.lastDial1Pos = 0
		self.lastDial2Pos = 0
		super().__init__()

	def toEight(self, fio) :
		''' pretty format a number and do unit conversion '''
		if self.IsMetric :
			return '%5.3f' % fio
		else :
			return '%4.4f' % (fio/25.4)

	@property
	def UnitStr(self) :
		''' unit of measure string '''
		return ('mm' if self.IsMetric else 'inch')

	@property
	def AxisIdx(self) :
		''' current axis as an integer index '''
		return 'XYZ'.find(self.whichAxis)

	def DrawValues(self,x,y,z) :
		''' draw the X,Y,Z values and cache the text '''
		a = self.toEight(x)
		if a != self.Xtext :
			self.XInfoBox.DrawText(a)
			self.Xtext = a
		a = self.toEight(y)
		if a != self.Ytext :
			self.YInfoBox.DrawText(a)
			self.Ytext = a
		a = self.toEight(z)
		if a != self.Ztext :
			self.ZInfoBox.DrawText(a)
			self.Ztext = a

	def DrawMachine(self,x,y,z) :
		''' draw the X,Y,Z values and cache the text '''
		a = self.toEight(x)
		if a != self.Xmtext :
			self.XMachBox.DrawText(a)
			self.mXtext = a
		a = self.toEight(y)
		if a != self.Ymtext :
			self.YMachBox.DrawText(a)
			self.Ymtext = a
		a = self.toEight(z)
		if a != self.Zmtext :
			self.ZMachBox.DrawText(a)
			self.Zmtext = a

	def DrawTicsize(self) :
		''' draw the tic size '''
		u = self.HighlightColor if (self.dialEdit=='T' and self.Dial2Enabled) else self.BackColor
		self.TicSizeBox.SetText(backclr=u)
		a = self.toEight(self.ticSize)
		self.TicSizeBox.DrawText(a)

	def DrawDevice(self) :
		''' draw the device name and ip '''
		u = self.HighlightColor if self.dialEdit=='D' else self.BackColor
		self.DeviceLabel.SetText(GlobalPico()['device'])
		self.DeviceLabel.DrawText(GlobalPico()['device'])
		a = self.GetDeviceIp()
		if a is None :
			a = ''
		self.DeviceBox.SetText(a, backclr=u)
		self.DeviceBox.Draw()

	def DrawWhichAxis(self) :
		''' draw the axis '''
		self.WhichAxisBox.DrawText(self.whichAxis)

	def DrawDesired(self) :
		''' draw the desired value '''
		if self.desiredMove == None :
			self.DesiredBox.DrawText('--')
		else :
			a = self.toEight(self.desiredMove)
			self.DesiredBox.DrawText(a)

	def DrawSubUnit(self) :
		''' draw something to show ticsize editing is disabled '''
		subunit = self.UnitStr
		if not self.Dial2Enabled :
			subunit = subunit + ' *'
		self.SubUnitBox.DrawText(subunit)

	def HighltColor(self, axis) :
		return self.BackColor if (axis != self.whichAxis) else self.HighlightColor

	def DrawAxes(self) :
		self.XAxisBox.SetText(backclr = self.HighltColor('X'))
		self.XAxisBox.Draw()
		self.YAxisBox.SetText(backclr = self.HighltColor('Y'))
		self.YAxisBox.Draw()
		self.ZAxisBox.SetText(backclr = self.HighltColor('Z'))
		self.ZAxisBox.Draw()

	def DrawNetwork(self) :
		oled = GlobalLcd()
		oled.draw_filled_box(0, self.netBox.ypos, oled.displayWidth, self.netBox.font.height, self.BackColor)

		if self.dialEdit == 'N' :
			u = self.HighlightColor if (self.dialEdit=='N' and self.Dial2Enabled) else self.BackColor
			self.netBox.SetText('Network: %s' % GlobalPico()['wlan_ssid'], backclr=u)
			self.netBox.Draw()
			self.netBox.SetText('', backclr=self.BackColor)
		else :
			wlan = WLAN(STA_IF)
			isup = 'up' if wlan.active() else 'dn'
			ip = wlan.ifconfig()[0] # current ip address
			self.netBox.DrawText('Network: %s at %s : %s' % (isup, GlobalPico()['wlan_ssid'], ip ))

	def DrawStatics(self) :
		''' draw the labels '''
		# self.titleBox.SetText(just = None)
		self.titleBox.Draw()
		self.UnitBox.DrawText(self.UnitStr)
		self.DrawValues(100, 200.123, 432.789)
		self.WhichAxisLabel.Draw()
		self.TicSizeLabel.Draw()
		self.DrawSubUnit()
		self.DesiredLabel.Draw()
		self.DrawAxes()
		self.DrawWhichAxis()
		self.DrawTicsize()
		self.DrawDesired()
		self.DrawDevice()
		self.DrawNetwork()

	def Setup(self) :
		''' draw the base screen and set up variables '''
		self.Dial2Enabled = True
		self.ClearScreen()
		self.whichAxis = 'X'
		self.ticSize = 1		# 1 mm
		self.ticValue = 0
		self.desiredMove = None
		self.checkTime = ticks_ms()
		self.isParsing = False
		self.isGoing = False
		bigFont = 'fontLucida40'
		medFont = 'fontArial22'

		# create a couple of ioboxes for sizing first
		self.bigBox = self.MakeIoBox(bigFont)
		self.medBox = self.MakeIoBox(medFont)

		# now decide on position stuff
		self.yX = self.yTitle + self.bigBox.font.height + self.lspace
		self.yY = self.yX + self.bigBox.font.height + self.lspace
		self.yZ = self.yY + self.bigBox.font.height + self.lspace
		self.bigWidth = self.bigBox.drawer.GetStringWidth('0') # width of a big Zero

		self.xUserInfo = self.indent
		self.yDesired = self.yZ + self.bigBox.font.height + self.lspace*2
		self.ySpeedInfo = self.yDesired + self.medBox.font.height + self.lspace*2
		self.yAxisInfo = self.ySpeedInfo + self.medBox.font.height + self.lspace*2
		self.yDeviceInfo = self.yAxisInfo + self.medBox.font.height + self.lspace*2
		self.yNet = self.yDeviceInfo + self.medBox.font.height + self.lspace
		self.xUserData = self.xUserInfo + self.medBox.drawer.GetStringWidth('Tic Size') + 30

		gc.collect()
		print('memory free before iobox allocation = %d' % (gc.mem_free()))

		# font info and io boxes
		self.titleBox = self.MakeIoBox('fontArial28', self.indent, self.yTitle)
		self.titleBox.SetText('Jog Screen', just=IoBox.JUST_CENTER)
		
		self.netBox = self.MakeIoBox(medFont, self.indent, self.yNet)
		self.netBox.Resize(0, self.bigBox.font.height)

		xoffset = self.indent
		self.XAxisBox = self.MakeIoBox(bigFont, xoffset, self.yX)
		self.XAxisBox.SetText('X')
		self.YAxisBox = self.MakeIoBox(bigFont, xoffset, self.yY)
		self.YAxisBox.SetText('Y')
		self.ZAxisBox = self.MakeIoBox(bigFont, xoffset, self.yZ)
		self.ZAxisBox.SetText('Z')

		infoSize = 8 * self.bigWidth
		self.xXYZ = self.XAxisBox.xpos + self.bigWidth + self.indent # where the coords print
		self.XInfoBox = self.MakeIoBox(bigFont, self.xXYZ, self.yX)
		self.XInfoBox.SetText(cached = True, just = IoBox.JUST_RIGHT)
		self.XInfoBox.Resize(infoSize, self.bigBox.font.height)
		self.YInfoBox = self.MakeIoBox(bigFont, self.xXYZ, self.yY)
		self.YInfoBox.SetText(cached = True, just = IoBox.JUST_RIGHT)
		self.YInfoBox.Resize(infoSize, self.bigBox.font.height)
		self.ZInfoBox = self.MakeIoBox(bigFont, self.xXYZ, self.yZ)
		self.ZInfoBox.SetText(cached = True, just = IoBox.JUST_RIGHT)
		self.ZInfoBox.Resize(infoSize, self.bigBox.font.height)
		# print("Axis boxes are at %d , %d" % ( self.xXYZ, self.yX))
		# print("Axis boxes sizes %d x %d" % (infoSize, self.bigBox.font.height))

		self.xXYZData = self.XInfoBox.xpos + self.XInfoBox.width + self.bigWidth * 1 # where machine coords print
		machOff =  self.xXYZData
		machFont = bigFont
		self.XMachBox = self.MakeIoBox(machFont, machOff, self.yX)
		self.XMachBox.SetText(cached = True, just = IoBox.JUST_RIGHT)
		self.XMachBox.Resize(infoSize, self.bigBox.font.height)
		self.YMachBox = self.MakeIoBox(machFont, machOff, self.yY)
		self.YMachBox.SetText(cached = True, just = IoBox.JUST_RIGHT)
		self.YMachBox.Resize(infoSize, self.bigBox.font.height)
		self.ZMachBox = self.MakeIoBox(machFont, machOff, self.yZ)
		self.ZMachBox.SetText(cached = True, just = IoBox.JUST_RIGHT)
		self.ZMachBox.Resize(infoSize, self.bigBox.font.height)
		# print("Mach boxes are at %d , %d" % ( machOff, self.yX))
		# print("Mach boxes sizes %d x %d" % (infoSize, self.bigBox.font.height))

		medsize = self.medBox.drawer.GetStringWidth('00000.00000')
		self.WhichAxisLabel = self.MakeIoBox(medFont,  self.xUserInfo, self.yAxisInfo)
		self.WhichAxisLabel.SetText('Axis')
		self.WhichAxisBox =  self.MakeIoBox(medFont,  self.xUserData, self.yAxisInfo)
		self.WhichAxisBox.SetText(just = IoBox.JUST_RIGHT)
		self.WhichAxisBox.Resize(medsize)
		self.TicSizeLabel = self.MakeIoBox(medFont,  self.xUserInfo, self.ySpeedInfo)
		self.TicSizeLabel.SetText('Tic Size')
		self.TicSizeBox =  self.MakeIoBox(medFont,  self.xUserData, self.ySpeedInfo)
		self.TicSizeBox.SetText(just = IoBox.JUST_RIGHT)
		self.TicSizeBox.Resize(medsize)
		self.DesiredLabel = self.MakeIoBox(medFont,  self.xUserInfo, self.yDesired)
		self.DesiredLabel.SetText('Desired')
		self.DesiredBox = self.MakeIoBox(medFont,  self.xUserData, self.yDesired)
		self.DesiredBox.SetText(just = IoBox.JUST_RIGHT)
		self.DesiredBox.Resize(medsize)
		# device label is different
		self.DeviceLabel = self.MakeIoBox(medFont,  self.indent, self.yDeviceInfo)
		devlabelmax = self.DeviceLabel.drawer.GetStringWidth('maxlabel') # max width ???
		self.DeviceLabel.Resize(devlabelmax, self.DeviceLabel.drawer.font.height)
		self.DeviceLabel.SetText(just=IoBox.JUST_RIGHT)
		self.DeviceBox = self.MakeIoBox(medFont, self.DeviceLabel.xpos + self.DeviceLabel.width + self.indent, self.yDeviceInfo)
		devsize = self.DeviceBox.drawer.GetStringWidth('https://000.000.000.000  ') # max width ???
		self.DeviceBox.Resize(devsize, self.DeviceBox.drawer.font.height)

		unitWidth =  self.titleBox.drawer.GetStringWidth('000000')
		self.UnitBox = self.MakeIoBox('fontArial28', GlobalLcd().displayWidth - unitWidth, self.yTitle)
		self.UnitBox.Resize(unitWidth-1, self.UnitBox.font.height)

		self.SubUnitBox = self.MakeIoBox(medFont, self.TicSizeBox.xpos + self.TicSizeBox.width + self.indent, self.TicSizeBox.ypos)
		self.SubUnitBox.Resize(self.SubUnitBox.drawer.GetStringWidth('inch * '), self.SubUnitBox.drawer.font.height) # largest field value

		gc.collect()
		print('memory free after iobox allocation = %d' % (gc.mem_free()))

		self.DrawStatics()

	def GetDeviceIp(self) :
		s = None
		try :
			s = GlobalPico()['device']
			s = GlobalPico()[s]['ip']
			if (s is not None) and (s[0] == '0') :
				s = None
		except Exception as e:
			print('dip: ' + str(e))
		finally:
			return s

	def UpdatePosition(self, data) :
		try :
			status = json.loads(data)
			self.Locn = status['pos']
			self.Mach = status['machine']
			posn = self.Locn
			self.DrawValues(posn[0], posn[1], posn[2])
			if self.showMachine :
				posn = self.Mach
				self.DrawMachine(posn[0], posn[1], posn[2])
		except Exception as e:
			print('update: ' + str(e))

	async def _statusRequest(self) :
		''' send and parse the result of an RRF status request'''
		if self.isParsing or self.isGoing:
			return
		self.isParsing = True
		try :
			u = None
			s = self.GetDeviceIp()
			if s is not None :
				print('request rr_status')
				u = await arequest.get(s + '/rr_status')
				if u is not None :
					# u.close() # required for mem cleanup ?
					self.UpdatePosition(u.content)
		except Exception as e:
			print('pst: ' + s + '  ' + (' ' if u is None else u.text))
		finally :
			self.isParsing = False

	def _parseStatus(self) :
		 task = asyncio.create_task(self._statusRequest())
		 return task

	async def _SendGoTo(self, axis, position) :
		''' send and parse the result of an RRF status request'''
		if self.isGoing :
			return None
		u = ticks_ms()
		self.isGoing = True # stop further parses from happening
		while self.isParsing and ticks_diff(ticks_ms(), u) < 6000 :
			asyncio.sleep_ms(200)
		# move in mm?
		try :
			gcode = '/rr_gcode?gcode=G0' + axis + str(position)
			s = self.GetDeviceIp()
			if s is not None :
				print('gcode = %s' % gcode)
				u = await arequest.get(s + gcode)
				#if u is not None :
				#	self.UpdatePosition(u.content) # ['body'])
				#	u.close() # required for mem cleanup
		except Exception as e:
			print('goto: ' + str(e))
		finally :
			self.isGoing = False

	def _sendGoRequest(self, axis, position) :
		 task = asyncio.create_task(self._SendGoTo(axis, position))
		 return task


	def HandleDial1(self) :
		''' set location by rotary and units of measure via button'''
		# switch to metric if clicked down
		u = self.Dial1.ButtonClicked
		# swap on click only
		if u :
			if self.showMachine == False :
				self.showMachine = True
				psn = self.Mach
				self.DrawMachine(psn[0], psn[1], psn[2])
			else :
				self.showMachine = False
				self.didCheck = True
				GlobalPico()['units'] = ('i' if self.IsMetric else 'm')
				self.ClearScreen()
				self.DrawStatics()

		# read position
		u = self.Dial1.Position
		if u != self.lastDial1Pos and self.dialEdit == 'T':
			if u == 0 :
				newtic = None
			else:
				newtic = self.ticSize * self.Dial1.Position + self.currentPos # use maybe newer dial1
			if newtic != self.desiredMove :
				# self.didCheck = True
				self.desiredMove = newtic
				self.DrawDesired()
				u = ticks_ms()
				self.moveTime = ticks_add(u, 300)
				self.checkTime = ticks_add(u, 1000)
		self.lastDial1Pos = self.Dial1.Position

	def HandleDial2(self) :
		# swap on click
		if  self.Dial2.ButtonClicked :
			if self.dialEdit == 'T' :
				self.Dial2Enabled = not self.Dial2Enabled
				if self.Dial2Enabled :
					self.Dial2.Position = self.ticValue
			self.didCheck = True
			self.DrawTicsize()
			self.DrawSubUnit()

		po = self.Dial2.Position
		if po != self.lastDial2Pos :
			self.lastDial2Pos = po
			if self.dialEdit == 'T' :	# tic size
				if not self.Dial2Enabled :
					return
				p1 = min(14, max(0, po))
				if p1 != po :
					self.Dial2.Position = p1
					self.lastDial2Pos = p1
				if p1 != self.ticValue :
					self.ticValue = p1
					decade = int(p1 / 3) # so 0...4
					maxval = 10 if self.IsMetric else 25.4
					newtic =  maxval * (10 ** (decade - 4)) * [1,2,5][p1 - decade * 3] # in mm
					self.didCheck = True
					self.ticSize = newtic # in mm
					self.DrawTicsize()
					self.Dial1.Position = 0
					self.desiredMove = None
					self.DrawDesired()
			elif self.dialEdit == 'D' :	# device
				devices = GlobalPico()['devices']
				p1 = po % len(devices)
				if devices[p1] != GlobalPico()['device'] :
					GlobalPico()['device'] = devices[p1]
					self.DrawDevice()
					self.didCheck = True
					self.Dial1.Position = 0
					self.lastDial1Pos = 0
					self.desiredMove = None
					self.DrawDesired()
			elif self.dialEdit == 'N' :	# device
				devices = GlobalPico()['wlan_ssids']
				p1 = po % len(devices)
				if devices[p1] != GlobalPico()['wlan_ssid'] :
					GlobalPico()['wlan_ssid'] = devices[p1]
					self.DrawNetwork()
			elif self.dialEdit == 'B' : # brightness
				p1 = min(20, max(0, po))
				if p1 != po :
					self.Dial2.Position = p1
				if self.Brightness != p1 :
					GlobalLcd().set_brightness(5 * p1)
					self.Brightness = p1


	def HandleSwitch(self) :
		u = self.Switch.Switch
		if u >= 0 and u <= 2 :
			amm = 'XYZ'[u]
			if amm != self.whichAxis :
				self.didCheck = True
				self.whichAxis = amm
				self.DrawWhichAxis()
				self.DrawAxes()
				self.Dial1.Position = 0

	def HandleTouch(self) :
		if not self.Dial2Enabled :
			return
		u = ticks_ms()
		tdif = ticks_diff(u, self.WhenTouch)
		tch = GlobalLcd().touch_get(True) # touchdown, downx, downy, touchx, touchy
		istouch = tch[1] != self.LastTouch[1] # activity
		if self.isTouchDown and not istouch : # released
			self.isTouchDown = False
		if istouch :
			self.LastTouch = tch
			self.WhenTouch = ticks_ms()
		if istouch and not self.isTouchDown and tdif > 500 :
				self.isTouchDown = True
				# moved
				if self.dialEdit == 'B' :
					self.DrawNetwork()
					self.dialEdit = 'T'
					self.Dial2.Position = self.ticValue
					self.lastDial2Pos = self.ticValue
				elif self.dialEdit == 'T' :
					self.dialEdit = 'D'
					self.Dial2.Position = GlobalPico()['devices'].index(GlobalPico()['device'])
					self.lastDial2Pos = self.Dial2.Position
				elif self.dialEdit == 'D' :
					self.dialEdit = 'N'
					self.lastSsid = GlobalPico()['wlan_ssid']
					self.Dial2.Position = 0
					self.lastDial2Pos = self.Dial2.Position
					self.DrawNetwork()
				elif self.dialEdit == 'N' :
					# if it was network, set the network if necessary
					ssid =  GlobalPico()['wlan_ssid']
					if self.lastSsid != ssid :
						doConnect(ssid)
						self.lastSsid = ssid
					self.dialEdit = 'B'
					self.Dial2.Position = self.Brightness
					self.lastDial2Pos = self.Dial2.Position
					self.DrawNetwork() # draw this when dialedit is B
				self.didCheck = True
				self.LastTouch = tch
				self.DrawTicsize()
				self.DrawDevice()
		else :
			self.LastTouch = tch

	async def Loop(self) :
		self.Dial1.Position = 0
		self.Dial2.Position = 0
		self.didCheck = False
		self.checkTime = ticks_ms()
		self.moveTime = ticks_ms()
		self.currentPos = 0
		self.doRun = True

		''' do a control loop responding to stuff '''
		try :
			while self.doRun :
				# on timer request send to web
				await asyncio.sleep(0)
				if self.desiredMove != None and not self.isParsing and not self.isGoing and ticks_diff(self.moveTime, ticks_ms()) < 0 :
					if self.desiredMove != self.currentPos : # do a move
						self._sendGoRequest(self.whichAxis, self.desiredMove) # in mm
						self.desiredMove = None # don't keep trying...
						u = ticks_ms()
						self.checkTime = ticks_add(u, 1000)
						self.moveTime = ticks_add(u, 300)

				# only check position if we're in usual move mode
				await asyncio.sleep(0)
				if self.dialEdit=='T' and ticks_diff(self.checkTime, ticks_ms()) < 0 :
						self._parseStatus()		# update x,y,z
						if self.desiredMove is None :
							self.currentPos = self.Locn[self.AxisIdx]
							self.Dial1.Position = 0
						self.DrawDesired()
						u = ticks_ms()
						self.checkTime = ticks_add(u, 1000)
						self.moveTime = ticks_add(u, 200) # can move now

				self.HandleDial2()	# dial2 is the tic size and device
				await asyncio.sleep(0)

				self.HandleDial1()	# dial 1 is the location
				await asyncio.sleep(0)

				self.HandleSwitch()	# switch for axis
				await asyncio.sleep(0)

				self.HandleTouch() # check the touchscreen
				await asyncio.sleep(0)

				# if something changed, don't send to web for a bit
				if self.didCheck :
					self.checkTime = ticks_add(ticks_ms(),1000)
					self.didCheck = False
				await asyncio.sleep(0)

				u = self.Dial1.ButtonState
				if u and u == self.Dial2.ButtonState :
					self.doRun = False	# quit this
				await asyncio.sleep(0)
		except Exception as e:
			print("Fail: " + str(e))
		asyncio.new_event_loop()  # Clear retained state

	def CleanUp(self) :
		''' do any cleanup '''
		pass

